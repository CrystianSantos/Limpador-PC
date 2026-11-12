package com.limpador.model;

import java.util.ArrayList;
import java.util.List;

public class CleanRequest {
    private boolean authTemp;
    private boolean authRecycle;
    private boolean authDuplicates;
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

    public List<String> getSelectedCopies() {
        return selectedCopies;
    }

    public void setSelectedCopies(List<String> selectedCopies) {
        this.selectedCopies = selectedCopies;
    }
}
