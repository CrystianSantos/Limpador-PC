package com.limpador.model;

import com.limpador.util.FormatUtils;
import java.util.ArrayList;
import java.util.List;

public class CleanResult {
    private boolean success;
    private int deletedCount;
    private int skippedCount;
    private long freedBytes;
    private String freedFormatted;
    private List<String> messages = new ArrayList<>();

    public CleanResult() {
    }

    public CleanResult(boolean success, int deletedCount, int skippedCount, long freedBytes, List<String> messages) {
        this.success = success;
        this.deletedCount = deletedCount;
        this.skippedCount = skippedCount;
        this.freedBytes = freedBytes;
        this.freedFormatted = FormatUtils.formatSize(freedBytes);
        this.messages = messages;
    }

    public boolean isSuccess() {
        return success;
    }

    public void setSuccess(boolean success) {
        this.success = success;
    }

    public int getDeletedCount() {
        return deletedCount;
    }

    public void setDeletedCount(int deletedCount) {
        this.deletedCount = deletedCount;
    }

    public int getSkippedCount() {
        return skippedCount;
    }

    public void setSkippedCount(int skippedCount) {
        this.skippedCount = skippedCount;
    }

    public long getFreedBytes() {
        return freedBytes;
    }

    public void setFreedBytes(long freedBytes) {
        this.freedBytes = freedBytes;
        this.freedFormatted = FormatUtils.formatSize(freedBytes);
    }

    public String getFreedFormatted() {
        return freedFormatted;
    }

    public List<String> getMessages() {
        return messages;
    }

    public void setMessages(List<String> messages) {
        this.messages = messages;
    }
}
