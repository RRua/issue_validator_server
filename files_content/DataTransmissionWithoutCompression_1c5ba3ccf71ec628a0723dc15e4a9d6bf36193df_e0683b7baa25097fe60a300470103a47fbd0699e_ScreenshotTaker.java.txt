/*
 *   Graph89 - Emulator for Android
 *  
 *	 Copyright (C) 2012-2013  Dritan Hashorva
 *
 *   This program is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.

 *   You should have received a copy of the GNU General Public License
 *   along with this program.  If not, see <http://www.gnu.org/licenses/>
 */

package com.graph89.controls;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;

import android.app.AlertDialog;
import android.app.Dialog;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.DialogInterface;
import android.graphics.Bitmap;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.provider.MediaStore;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import com.Bisha.TI89EmuDonation.R;
import com.graph89.common.Util;
import com.graph89.emulationcore.EmulatorActivity;

public class ScreenshotTaker
{
	private Context		mContext			= null;

	public ScreenshotTaker(Context context)
	{
		mContext = context;
	}

	public void ShowDialog()
	{
		final EmulatorActivity activity = (EmulatorActivity) mContext;

		if (!Util.IsStorageAvailable(activity))
		{
			return;
		}

		final View view = LayoutInflater.from(mContext).inflate(R.layout.take_screenshot, (ViewGroup) activity.findViewById(R.id.take_screenshot_layout));
		final TextView constantpath = (TextView) view.findViewById(R.id.take_screenshot_readonly_path);
		final EditText filenameEdit = (EditText) view.findViewById(R.id.take_screenshot_path);

		// retrieve media storage path
		String pathMessage = " (Check /Pictures or /DCIM)";
		try {
			Uri imageCollection = MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
			pathMessage = imageCollection + pathMessage;
		} catch (Exception e) {
			Log.d("graph89", "caught exception finding MediaStore.Images path: "+e.toString());
		}
		constantpath.setText(pathMessage);

		String dateNow = Util.getTimestamp();
		filenameEdit.setText(dateNow + ".png");
		filenameEdit.setSelection(dateNow.length());

		final AlertDialog d = new AlertDialog.Builder(mContext).setView(view).setTitle("Take Screenshot").setPositiveButton(android.R.string.ok, new Dialog.OnClickListener()
		{
			@Override
			public void onClick(DialogInterface d, int which)
			{
			}
		}).setNegativeButton(android.R.string.cancel, new Dialog.OnClickListener()
		{
			@Override
			public void onClick(DialogInterface d, int which)
			{
				activity.HideKeyboard();
			}
		}).create();

		d.setOnShowListener(new DialogInterface.OnShowListener()
		{
			@Override
			public void onShow(DialogInterface dialog)
			{
				Button b = d.getButton(AlertDialog.BUTTON_POSITIVE);
				b.setOnClickListener(new View.OnClickListener()
				{
					@Override
					public void onClick(View view)
					{
						String filename = filenameEdit.getText().toString().trim();
						filename = filename.replace("/", "");

						if (filename.length() > 0)
						{
							if (!filename.endsWith(".png")) filename += ".png";

							Bitmap image = EmulatorActivity.CurrentSkin.Screen.getScreenShot();
							if (image != null)
							{
								try
								{
									// access the images media store
									ContentResolver resolver = mContext.getContentResolver();
									Uri imageCollection = MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);

									// Get a URI for the new file
									ContentValues newImageDetails = new ContentValues();
									newImageDetails.put(MediaStore.Images.Media.DISPLAY_NAME, filename);
									Uri imageUri = resolver.insert(imageCollection, newImageDetails);
									Log.d("graph89", "imageUri="+imageUri.toString());

									// open the output file
									OutputStream out = mContext.getContentResolver().openOutputStream(imageUri);
									image.compress(Bitmap.CompressFormat.PNG, 90, out);
									out.close();

									Util.ShowAlert((EmulatorActivity) mContext, "Screenshot", "Successfully saved emulated screen to " + filename);
								}
								catch (Exception e)
								{
									Util.ShowAlert((EmulatorActivity) mContext, "Error taking screenshot", e);
								}
							}

							activity.HideKeyboard();
							d.dismiss();
						}
					}
				});
			}
		});
		d.setCanceledOnTouchOutside(false);
		activity.ShowKeyboard();
		d.show();
	}
}
