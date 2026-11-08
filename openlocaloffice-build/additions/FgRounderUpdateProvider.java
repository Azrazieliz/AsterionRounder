package com.openlocal.office.core;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.UriMatcher;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;

import java.io.File;
import java.io.FileNotFoundException;

/** The Android system installer receives one verified private-cache APK.
 * No other application files are exposed, and writes are forbidden.
 */
public final class FgRounderUpdateProvider extends ContentProvider {
    public static final String AUTHORITY="com.openlocal.office.rounderupdates";
    public static final Uri APK=Uri.parse("content://"+AUTHORITY+"/signed-update.apk");
    public static File stagedFile(android.content.Context context){
        return new File(new File(context.getCacheDir(),"rounder-updates"),"verified-release.apk");
    }
    @Override public boolean onCreate(){return true;}
    @Override public String getType(Uri uri){
        return APK.equals(uri)?"application/vnd.android.package-archive":null;
    }
    private File validate(Uri uri)throws FileNotFoundException {
        if(!APK.equals(uri))throw new FileNotFoundException("Unsupported update URI");
        File file=stagedFile(getContext());
        if(!file.isFile()||file.length()<4096L)
            throw new FileNotFoundException("No verified update is staged");
        return file;
    }
    @Override public ParcelFileDescriptor openFile(Uri uri,String mode)
            throws FileNotFoundException {
        if(!"r".equals(mode))throw new FileNotFoundException("Read only update provider");
        return ParcelFileDescriptor.open(validate(uri),ParcelFileDescriptor.MODE_READ_ONLY);
    }
    @Override public Cursor query(Uri uri,String[] projection,String selection,
            String[] selectionArgs,String sortOrder) {
        try{
            File file=validate(uri);
            String[] cols=(projection==null||projection.length==0)?
                new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE}:projection;
            MatrixCursor cursor=new MatrixCursor(cols);
            Object[] data=new Object[cols.length];
            for(int i=0;i<cols.length;i++){
                if(OpenableColumns.DISPLAY_NAME.equals(cols[i]))
                    data[i]="Asterion-Rounder-update.apk";
                else if(OpenableColumns.SIZE.equals(cols[i]))data[i]=file.length();
                else data[i]=null;
            }
            cursor.addRow(data);
            return cursor;
        }catch(FileNotFoundException missing){return null;}
    }
    @Override public Uri insert(Uri uri,ContentValues values){
        throw new UnsupportedOperationException("Update provider is read only");
    }
    @Override public int update(Uri uri,ContentValues values,
                                String selection,String[] selectionArgs){
        throw new UnsupportedOperationException("Update provider is read only");
    }
    @Override public int delete(Uri uri,String selection,String[] selectionArgs){
        throw new UnsupportedOperationException("Update provider is read only");
    }
}