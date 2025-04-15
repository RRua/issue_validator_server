package com.example.halftough.webcomreader.activities.ReadChapter;


import android.content.Intent;
import android.os.Bundle;
import android.os.PersistableBundle;
import android.support.v7.app.AppCompatActivity;
import android.support.v7.widget.Toolbar;
import android.util.Log;

import com.example.halftough.webcomreader.NoWebcomClassException;
import com.example.halftough.webcomreader.R;
import com.example.halftough.webcomreader.UserRepository;
import com.example.halftough.webcomreader.activities.ChapterList.ChapterListActivity;
import com.example.halftough.webcomreader.activities.MyWebcoms.MyWebcomsActivity;
import com.example.halftough.webcomreader.database.ReadChapterRepository;
import com.example.halftough.webcomreader.webcoms.Webcom;

public class ReadChapterActivity extends AppCompatActivity {
    private Webcom webcom;
    ComicPageView readChapterImage;
    ReadChapterRepository readChapterRepository;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.read_chapter_activity);
        Toolbar toolbar = (Toolbar) findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);

        readChapterImage = (ComicPageView)findViewById(R.id.readChapterImage);

        Intent intent = getIntent();
        try {
            webcom = UserRepository.getWebcomInstance( intent.getStringExtra(MyWebcomsActivity.WEBCOM_ID) );
        } catch (NoWebcomClassException e) {
            //TODO exception
            e.printStackTrace();
        }

        readChapterRepository = new ReadChapterRepository(this, webcom, readChapterImage);
        setChapter( intent.getStringExtra(ChapterListActivity.CHAPTER_NUMBER) );
    }

    @Override
    public void onSaveInstanceState(Bundle savedInstance) {
        String number = readChapterRepository.getChapterNumber();
        savedInstance.putString(ChapterListActivity.CHAPTER_NUMBER, number);
        super.onSaveInstanceState(savedInstance);
    }

    @Override
    protected void onRestoreInstanceState(Bundle savedInstanceState) {
        super.onRestoreInstanceState(savedInstanceState);
        String number = savedInstanceState.getString(ChapterListActivity.CHAPTER_NUMBER);
        setChapter(number);
    }

    @Override
    protected void onResume() {
        super.onResume();
        readChapterImage.start();
    }

    @Override
    protected void onPause() {
        super.onPause();
        readChapterImage.stop();
    }

    @Override
    public void onBackPressed() {
        readChapterImage.stop();
        Intent result = new Intent();
        result.putExtra(ChapterListActivity.UPDATE_LIST, readChapterRepository.getUpdateMarker());
        setResult(RESULT_OK, result);
        super.onBackPressed();
    }

    public void setChapter(String c){
        readChapterRepository.setChapter(c);
    }

    public void nextPage() {
        readChapterRepository.nextChapter();
    }

    public void previousPage() {
        readChapterRepository.previousChapter();
    }
}
