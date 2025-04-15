/*
 * Copyright 2016 The TensorFlow Authors. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.lun.chin.aicamera.oldCode;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.hardware.Camera;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.Image.Plane;
import android.media.ImageReader;
import android.media.ImageReader.OnImageAvailableListener;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Trace;
import android.support.v4.app.Fragment;
import android.support.v7.app.AppCompatActivity;
import android.util.Size;
import android.view.KeyEvent;
import android.view.Surface;
import android.view.View;
import android.view.WindowManager;
import android.widget.Toast;

import com.lun.chin.aicamera.listener.CameraChangedListener;
import com.lun.chin.aicamera.GalleryViewPagerFragment;
import com.lun.chin.aicamera.ImageManager;
import com.lun.chin.aicamera.OverlayView;
import com.lun.chin.aicamera.R;
import com.lun.chin.aicamera.RecyclerViewFragment;
import com.lun.chin.aicamera.listener.RunInBackgroundListener;
import com.lun.chin.aicamera.env.ImageUtils;
import com.lun.chin.aicamera.env.Logger;

import org.opencv.android.BaseLoaderCallback;
import org.opencv.android.LoaderCallbackInterface;
import org.opencv.android.OpenCVLoader;

import java.nio.ByteBuffer;


public abstract class CameraActivity extends AppCompatActivity
        implements
            OnImageAvailableListener,
            Camera.PreviewCallback,
        CameraFragment.OnCameraButtonClickedListener,
        RunInBackgroundListener {

    private static final Logger LOGGER = new Logger();

    private static final int PERMISSIONS_REQUEST = 1;

    private static final String PERMISSION_CAMERA = Manifest.permission.CAMERA;
    private static final String PERMISSION_STORAGE = Manifest.permission.WRITE_EXTERNAL_STORAGE;

    private boolean mDebug = false;

    private Handler mHandler;
    private HandlerThread mHandlerThread;
    private boolean mIsProcessingFrame = false;
    private boolean mIsProcessingPreviewFrame = false;
    private byte[][] mYuvBytes = new byte[3][];
    private int[] mRgbBytes = null;
    private int[] mRgbBytesPreview = null;
    private int mYRowStride;
    private byte[] mPictureBytes;

    protected boolean mUseCamera2API;
    protected int mPreviewWidth = 0;
    protected int mPreviewHeight = 0;
    protected int mPictureWidth = 0;
    protected int mPictureHeight = 0;

    private Runnable mPostInferenceCallback;
    private Runnable mPostPreviewInferenceCallback;
    private Runnable mImageConverter;
    private Runnable mPreviewImageConverter;

    private int mRotation = 90;
    protected String mFilename;

    private BaseLoaderCallback _baseLoaderCallback = new BaseLoaderCallback(this) {
        @Override
        public void onManagerConnected(int status) {
            switch (status) {
                case LoaderCallbackInterface.SUCCESS: {
                    LOGGER.d("OpenCV loaded successfully");
                    // Load ndk built module, as specified in moduleName in build.gradle
                    // after opencv initialization
                    System.loadLibrary("native-lib");
                }
                break;
                default: {
                    super.onManagerConnected(status);
                }
            }
        }
    };

    @Override
    protected void onCreate(final Bundle savedInstanceState) {
        LOGGER.d("onCreate " + this);
        super.onCreate(null);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        setContentView(R.layout.activity_camera_old);

        if (hasPermission()) {
            setFragment();
        } else {
            requestPermission();
        }
    }

    private byte[] lastPreviewFrame;

    protected int[] getRgbBytes() {
        mImageConverter.run();
        return mRgbBytes;
    }

    protected byte[] getPictureBytes() {
        return mPictureBytes;
    }

    protected int[] getRgbBytesPreview() {
        mPreviewImageConverter.run();
        return mRgbBytesPreview;
    }

    protected int getLuminanceStride() {
        return mYRowStride;
    }

    protected byte[] getLuminance() {
        return mYuvBytes[0];
    }

    /**
     * Callback for android.hardware.Camera API
     */
    @Override
    public void onPreviewFrame(final byte[] bytes, final Camera camera) {
        if (mIsProcessingPreviewFrame) {
            LOGGER.w("Dropping frame!");
            return;
        }

        mIsProcessingPreviewFrame = true;

        try {
            // Initialize the storage bitmaps once when the resolution is known.
            if (mRgbBytesPreview == null) {
                Camera.Size previewSize = camera.getParameters().getPreviewSize();
                mPreviewHeight = previewSize.height;
                mPreviewWidth = previewSize.width;
                mRgbBytesPreview = new int[mPreviewWidth * mPreviewHeight];
                onPreviewSizeChosen(new Size(previewSize.width, previewSize.height), 90);
            }
        } catch (final Exception e) {
            LOGGER.e(e, "Exception!");
            return;
        }

        mPreviewImageConverter =
                new Runnable() {
                    @Override
                    public void run() {
                        ImageUtils.convertYUV420SPToARGB8888(bytes,
                                mPreviewWidth,
                                mPreviewHeight,
                                mRgbBytesPreview);
                    }
                };

        mPostPreviewInferenceCallback =
                new Runnable() {
                    @Override
                    public void run() {
                        camera.addCallbackBuffer(bytes);
                        mIsProcessingPreviewFrame = false;
                    }
                };

        processPreview();
    }

    public void onCaptureStillFrame(final byte[] bytes, final Camera camera) {
        if (mIsProcessingFrame) {
            return;
        }

        final Long timeStamp = System.currentTimeMillis();
        mFilename = "IMG_" + timeStamp.toString() + ".png";
        ImageManager.getInstance().addPendingImage(mFilename);

        mIsProcessingFrame = true;

        // Initialize the storage bitmaps once when the resolution is known.
        if (mPictureBytes == null) {
            prepareBitmap(camera.getParameters().getPictureSize());
        }

        mPictureBytes = bytes;

        mPostInferenceCallback =
                new Runnable() {
                    @Override
                    public void run() {
                        camera.addCallbackBuffer(bytes);
                        mIsProcessingFrame = false;
                    }
                };

        processImage();
    }

    private void prepareBitmap(Camera.Size pictureSize) {
        try {
            mPictureHeight = pictureSize.height;
            mPictureWidth = pictureSize.width;
            onPictureSizeChosen(new Size(pictureSize.width, pictureSize.height), mRotation);
        } catch (final Exception e) {
            LOGGER.e(e, "Exception!");
            return;
        }
    }

    // Callback for when a still image is taken with the Camera2 API.
    @Override
    public void onImageAvailable(final ImageReader reader) {
        if (mPictureWidth == 0 || mPictureHeight == 0) {
            return;
        }
        try {
            final Image image = reader.acquireLatestImage();

            if (image == null) {
                return;
            }

            if (mIsProcessingFrame) {
                image.close();
                return;
            }
            mIsProcessingFrame = true;
            Trace.beginSection("imageAvailable");

            final Plane[] planes = image.getPlanes();
            fillBytes(planes, mYuvBytes);
            mYRowStride = planes[0].getRowStride();
            final int uvRowStride = planes[1].getRowStride();
            final int uvPixelStride = planes[1].getPixelStride();

            mImageConverter =
                    new Runnable() {
                        @Override
                        public void run() {
                            ImageUtils.convertYUV420ToARGB8888(
                                    mYuvBytes[0],
                                    mYuvBytes[1],
                                    mYuvBytes[2],
                                    mPictureWidth,
                                    mPictureHeight,
                                    mYRowStride,
                                    uvRowStride,
                                    uvPixelStride,
                                    mRgbBytes);
                        }
                    };

            mPostInferenceCallback =
                    new Runnable() {
                        @Override
                        public void run() {
                            image.close();
                            mIsProcessingFrame = false;
                        }
                    };

            processImage();
        } catch (final Exception e) {
            LOGGER.e(e, "Exception!");
            Trace.endSection();
            return;
        }
        Trace.endSection();
    }

    // Callback when preview image is available from the Camera2 API
    private void onPreviewImageAvailable(final ImageReader reader) {
        if (mPreviewWidth == 0 || mPreviewHeight == 0) {
            return;
        }
        try {
            final Image image = reader.acquireLatestImage();

            if (image == null) {
                LOGGER.i("image null");
                return;
            }

            if (mIsProcessingPreviewFrame) {
                LOGGER.i("processing preview true");
                image.close();
                return;
            }
            mIsProcessingPreviewFrame  = true;
            Trace.beginSection("imageAvailable");

            final Plane[] planes = image.getPlanes();
            fillBytes(planes, mYuvBytes);
            mYRowStride = planes[0].getRowStride();
            final int uvRowStride = planes[1].getRowStride();
            final int uvPixelStride = planes[1].getPixelStride();

            mPreviewImageConverter =
                    new Runnable() {
                        @Override
                        public void run() {
                            ImageUtils.convertYUV420ToARGB8888(
                                    mYuvBytes[0],
                                    mYuvBytes[1],
                                    mYuvBytes[2],
                                    mPreviewWidth,
                                    mPreviewHeight,
                                    mYRowStride,
                                    uvRowStride,
                                    uvPixelStride,
                                    mRgbBytesPreview);
                        }
                    };

            mPostPreviewInferenceCallback =
                    new Runnable() {
                        @Override
                        public void run() {
                            image.close();
                            mIsProcessingPreviewFrame = false;
                        }
                    };

            processPreview();
        } catch (final Exception e) {
            LOGGER.e(e, "Exception!");
            Trace.endSection();
            return;
        }
        Trace.endSection();
    }

    @Override
    public synchronized void onStart() {
        LOGGER.d("onStart " + this);
        super.onStart();
    }

    @Override
    public synchronized void onResume() {
        LOGGER.d("onResume " + this);
        super.onResume();

        if (!OpenCVLoader.initDebug()) {
            LOGGER.d("Internal OpenCV library not found. Using OpenCV Manager for initialization");
            OpenCVLoader.initAsync(OpenCVLoader.OPENCV_VERSION_3_0_0, this, _baseLoaderCallback);
        } else {
            LOGGER.d("OpenCV library found inside package. Using it!");
            _baseLoaderCallback.onManagerConnected(LoaderCallbackInterface.SUCCESS);
        }

        mHandlerThread = new HandlerThread("inference");
        mHandlerThread.start();
        mHandler = new Handler(mHandlerThread.getLooper());
    }

    @Override
    public synchronized void onPause() {
        LOGGER.d("onPause " + this);
        super.onPause();
    }

    @Override
    public synchronized void onStop() {
        LOGGER.d("onStop " + this);
        super.onStop();
    }

    @Override
    public synchronized void onDestroy() {
        LOGGER.d("onDestroy " + this);

        mHandlerThread.quitSafely();
        try {
            mHandlerThread.join();
            mHandlerThread = null;
            mHandler = null;
        } catch (final InterruptedException e) {
            LOGGER.e(e, "Exception!");
        }

        super.onDestroy();
    }

    protected synchronized void runInBackground(final Runnable r) {
        if (mHandler != null) {
            mHandler.post(r);
        }
    }

    @Override
    public void onRequestPermissionsResult(
            final int requestCode, final String[] permissions, final int[] grantResults) {
        if (requestCode == PERMISSIONS_REQUEST) {
            if (grantResults.length > 0
                    && grantResults[0] == PackageManager.PERMISSION_GRANTED
                    && grantResults[1] == PackageManager.PERMISSION_GRANTED) {
                setFragment();
            } else {
                requestPermission();
            }
        }
    }

    @Override
    public void onCameraButtonClicked(View v) {
        switch (v.getId()) {
            case R.id.goto_gallery:
                GalleryViewPagerFragment galleryViewPagerFragment =
                        GalleryViewPagerFragment.newInstance(
                                0, ImageManager.getInstance().getImageItems());

                getSupportFragmentManager()
                        .beginTransaction()
                        .replace(R.id.container, galleryViewPagerFragment)
                        .addToBackStack(null)
                        .commit();

                // TODO improve the loading speed of the gallery page. Remove it for now.
                /*
                RecyclerViewFragment fragment
                        = RecyclerViewFragment.newInstance(
                                ImageManager.getInstance().getImageItems());

                getSupportFragmentManager()
                        .beginTransaction()
                        .replace(R.id.container, fragment)
                        .addToBackStack(null)
                        .commit();
                */
                break;
        }
    }

    @Override
    public void run(Runnable runnable) {
        runInBackground(runnable);
    }

    private boolean hasPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            return checkSelfPermission(PERMISSION_CAMERA) == PackageManager.PERMISSION_GRANTED &&
                    checkSelfPermission(PERMISSION_STORAGE) == PackageManager.PERMISSION_GRANTED;
        } else {
            return true;
        }
    }

    private void requestPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (shouldShowRequestPermissionRationale(PERMISSION_CAMERA) ||
                    shouldShowRequestPermissionRationale(PERMISSION_STORAGE)) {
                Toast.makeText(CameraActivity.this,
                        "Camera AND storage permission are required for this demo", Toast.LENGTH_LONG).show();
            }
            requestPermissions(new String[] {PERMISSION_CAMERA, PERMISSION_STORAGE}, PERMISSIONS_REQUEST);
        }
    }

    // Returns true if the device supports the required hardware level, or better.
    private boolean isHardwareLevelSupported(
            CameraCharacteristics characteristics, int requiredLevel) {
        int deviceLevel = characteristics.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL);
        if (deviceLevel == CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_LEGACY) {
            return requiredLevel == deviceLevel;
        }
        // deviceLevel is not LEGACY, can use numerical sort
        return requiredLevel <= deviceLevel;
    }

    private String chooseCamera() {
        final CameraManager manager = (CameraManager) getSystemService(Context.CAMERA_SERVICE);
        try {
            for (final String cameraId : manager.getCameraIdList()) {
                final CameraCharacteristics characteristics = manager.getCameraCharacteristics(cameraId);

                // We don't use a front facing camera in this sample.
                final Integer facing = characteristics.get(CameraCharacteristics.LENS_FACING);
                if (facing != null && facing == CameraCharacteristics.LENS_FACING_FRONT) {
                    continue;
                }

                final StreamConfigurationMap map =
                        characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);

                if (map == null) {
                    continue;
                }

                // Fallback to camera1 API for internal cameras that don't have full support.
                // This should help with legacy situations where using the camera2 API causes
                // distorted or otherwise broken previews.
                /*
                mUseCamera2API = (facing == CameraCharacteristics.LENS_FACING_EXTERNAL)
                        || isHardwareLevelSupported(characteristics,
                        CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_FULL);
                LOGGER.i("Camera API lv2?: %s", mUseCamera2API);
                */

                // TODO add support for Camera2 API.
                mUseCamera2API = false;
                return cameraId;
            }
        } catch (CameraAccessException e) {
            LOGGER.e(e, "Not allowed to access camera");
        }

        return null;
    }

    protected void setFragment() {
        String cameraId = chooseCamera();
        if (cameraId == null) {
            Toast.makeText(this, "No Camera Detected", Toast.LENGTH_SHORT).show();
            finish();
        }

        final Fragment fragment;
        if (mUseCamera2API) {
            LOGGER.i("Using Camera2 API");
            CameraConnectionFragment camera2Fragment =
                    CameraConnectionFragment.newInstance(
                            new CameraConnectionFragment.ConnectionCallback() {
                                @Override
                                public void onPreviewSizeChosen(final Size size, final int rotation) {
                                    mPreviewHeight = size.getHeight();
                                    mPreviewWidth = size.getWidth();
                                    CameraActivity.this.onPreviewSizeChosen(size, rotation);
                                }
                            },
                            this,
                            new OnImageAvailableListener() {
                                @Override
                                public void onImageAvailable(ImageReader reader) {
                                    onPreviewImageAvailable(reader);
                                }
                            },
                            getLayoutId(),
                            getDesiredPreviewFrameSize());

            camera2Fragment.setCamera(cameraId);
            fragment = camera2Fragment;
        } else {
            LOGGER.i("Using Camera API");
            fragment = LegacyCameraConnectionFragment.newInstance(
                    new Camera.PreviewCallback() {
                        @Override
                        public void onPreviewFrame(final byte[] data, final Camera camera) {
                            onCaptureStillFrame(data, camera);
                        }
                    },
                    null, //this,
                    new CameraChangedListener() {
                        @Override
                        public void onCameraChangedListener(Camera camera, boolean isFrontFacing) {
                            mRotation = isFrontFacing ? -90 : 90;
                            prepareBitmap(camera.getParameters().getPictureSize());
                        }
                    },
                    getLayoutId(),
                    getDesiredPreviewFrameSize());
        }

        getSupportFragmentManager()
                .beginTransaction()
                .replace(R.id.container, fragment)
                .commit();
    }

    protected void fillBytes(final Plane[] planes, final byte[][] yuvBytes) {
        // Because of the variable row stride it's not possible to know in
        // advance the actual necessary dimensions of the yuv planes.
        for (int i = 0; i < planes.length; ++i) {
            final ByteBuffer buffer = planes[i].getBuffer();
            if (yuvBytes[i] == null) {
                LOGGER.d("Initializing buffer %d at size %d", i, buffer.capacity());
                yuvBytes[i] = new byte[buffer.capacity()];
            }
            buffer.get(yuvBytes[i]);
        }
    }

    public boolean isDebug() {
        return mDebug;
    }

    public void requestRender() {
        final OverlayView overlay = (OverlayView) findViewById(R.id.debug_overlay);
        if (overlay != null) {
            overlay.postInvalidate();
        }
    }

    public void addCallback(final OverlayView.DrawCallback callback) {
        final OverlayView overlay = (OverlayView) findViewById(R.id.debug_overlay);
        if (overlay != null) {
            overlay.addCallback(callback);
        }
    }

    public void onSetDebug(final boolean debug) {}

    @Override
    public boolean onKeyDown(final int keyCode, final KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_VOLUME_DOWN || keyCode == KeyEvent.KEYCODE_VOLUME_UP
                || keyCode == KeyEvent.KEYCODE_BUTTON_L1 || keyCode == KeyEvent.KEYCODE_DPAD_CENTER) {
            mDebug = !mDebug;
            requestRender();
            onSetDebug(mDebug);
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    protected void readyForNextImage() {
        if (mPostInferenceCallback != null) {
            mPostInferenceCallback.run();
        }
    }

    protected void readyForNextPreviewImage() {
        if (mPostPreviewInferenceCallback != null) {
            mPostPreviewInferenceCallback.run();
        }
    }

    protected int getScreenOrientation() {
        switch (getWindowManager().getDefaultDisplay().getRotation()) {
            case Surface.ROTATION_270:
                return 270;
            case Surface.ROTATION_180:
                return 180;
            case Surface.ROTATION_90:
                return 90;
            default:
                return 0;
        }
    }

    protected void notifyFragmentOfImageChange(String filename) {
        Fragment fragment = getSupportFragmentManager().findFragmentById(R.id.container);

        if (fragment != null && fragment.isAdded()) {
            if (fragment instanceof RecyclerViewFragment) {
                ((RecyclerViewFragment)fragment).notifyImageChange(filename);
            } else if (fragment instanceof GalleryViewPagerFragment) {
                ((GalleryViewPagerFragment)fragment).notifyImageChange(filename);
            }
        }
    }

    protected abstract void processImage();
    protected abstract void processPreview();
    protected abstract void onPreviewSizeChosen(final Size size, final int rotation);
    protected abstract void onPictureSizeChosen(final Size size, final int rotation);
    protected abstract int getLayoutId();
    protected abstract Size getDesiredPreviewFrameSize();
}
