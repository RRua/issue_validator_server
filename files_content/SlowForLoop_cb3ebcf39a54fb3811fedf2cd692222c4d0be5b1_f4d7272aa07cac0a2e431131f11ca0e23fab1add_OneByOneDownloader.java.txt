package com.example.halftough.webcomreader;

import java.util.Queue;

public abstract class OneByOneDownloader<ElementType, Extra> {
    protected int capacity;
    protected int free;
    protected boolean downloading = false;
    Queue<ElementType> queue;
    Queue<Extra> extras;

    public void add(ElementType element, Extra extra){
        queue.add(element);
        if(extras != null){
            extras.add(extra);
        }
    }
    // Add to the list and start downloading, if it wasn't before
    public void enqueue(ElementType element, Extra extra){
        add(element, extra);
        download();
    }


    public void download(){
        if (!downloading) {
            while (free > 0 && !queue.isEmpty()) {
                downloading = true;
                free--;
                ElementType element  = queue.remove();
                Extra extra = extras!=null?extras.remove():null;

                downloadElement(element, extra);
            }
        }
    }

    protected abstract void downloadElement(ElementType element, final Extra extra);

    // Method that should be called on success of downloadElement.
    // Because ways of doing that may vary, extension of this class should remember to call it.
    protected void elementDownloaded(){
        if(!queue.isEmpty()) {
            ElementType element = queue.remove();
            Extra extra = extras!=null?extras.remove():null;

            downloadElement(element, extra);
        }
        else{
            free++;
            if(free==capacity)
                downloading = false;
        }
    }

}
