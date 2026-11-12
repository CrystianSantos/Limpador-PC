package com.limpador.model;

import java.util.ArrayList;
import java.util.List;

public class CleanRequest {
    private boolean authTemp;
    private boolean authRecycle;
    private boolean authDuplicates;
    private boolean deleteDuplicatesPermanently;
    private List<String> selectedCopies = new ArrayList<>();

    public CleanRequest() {
    }

    public boolean isAuthTemp() {
        return authTemp;
    }

    public void setAuthTemp(boolean authTemp) {
        this.authTemp = authTemp;
    }

    public boolean isAuthRecycle() {
        return authRecycle;
    }

    public void setAuthRecycle(boolean authRecycle) {
        this.authRecycle = authRecycle;
    }

    public boolean isAuthDuplicates() {
        return authDuplicates;
    }

    public void setAuthDuplicates(boolean authDuplicates) {
        this.authDuplicates = authDuplicates;
    }

    public boolean isDeleteDuplicatesPermanently() {
        return deleteDuplicatesPermanently;
    }

    public void setDeleteDuplicatesPermanently(boolean deleteDuplicatesPermanently) {
        this.deleteDuplicatesPermanently = deleteDuplicatesPermanently;
    }

    public List<String> getSelectedCopies() {
        return selectedCopies;
    }

    public void setSelectedCopies(List<String> selectedCopies) {
        this.selectedCopies = selectedCopies;
    }
}
