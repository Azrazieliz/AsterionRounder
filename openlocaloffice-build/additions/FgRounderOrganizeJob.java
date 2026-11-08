package com.openlocal.office.core;

import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;
import android.os.Build;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/** Opt-in bounded network work: scans known Downloader incoming destinations.
 * All source and destination data stay in the user's TeraBox account.
 */
public final class FgRounderOrganizeJob extends JobService {
    private static final int JOB_ID=153701;
    private static final long PERIOD=15L*60L*1000L;
    private final ExecutorService pool=Executors.newSingleThreadExecutor();
    private volatile FgRounderOrganizer organizer;
    private volatile Future<?> task;

    public static void schedule(Context context,boolean enable){
        JobScheduler jobs=(JobScheduler)context.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        if(jobs==null)return;
        if(!enable){jobs.cancel(JOB_ID);return;}
        JobInfo info=new JobInfo.Builder(JOB_ID,
            new ComponentName(context,FgRounderOrganizeJob.class))
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPeriodic(PERIOD)
            .setPersisted(false)
            .build();
        jobs.schedule(info);
    }
    @Override public boolean onStartJob(JobParameters params){
        task=pool.submit(()->{
            try{
                FgTeraboxClient cloud=new FgTeraboxClient(this);
                if(!cloud.configured())return;
                FgTeraboxSearchIndex idx=new FgTeraboxSearchIndex(this,cloud,
                    new FgTeraboxSearchIndex.Listener(){
                        @Override public void onSearch(String event){}
                        @Override public void onProgress(String event){}
                    });
                organizer=new FgRounderOrganizer(this,cloud,idx);
                if(organizer.autoEnabled()){
                    idx.ensure(false);
                    organizer.autoRun(event->
                        android.util.Log.i("FG_ORGANIZER","Background operation update"));
                }
            }catch(Exception failure){
                android.util.Log.w("FG_ORGANIZER",
                    "Background cycle paused: "+failure.getClass().getSimpleName());
            }finally{jobFinished(params,false);}
        });
        return true;
    }
    @Override public boolean onStopJob(JobParameters params){
        FgRounderOrganizer value=organizer;
        if(value!=null)value.stop();
        Future<?> pending=task;
        if(pending!=null)pending.cancel(true);
        return true;
    }
}
