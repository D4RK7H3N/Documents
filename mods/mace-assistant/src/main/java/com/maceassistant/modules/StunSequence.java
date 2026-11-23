package com.maceassistant.modules;

/** One axe hit breaks the shield; the axe attempt starts a short suppression. */
final class StunSequence {
    enum Stage { IDLE, AXE }

    private Stage stage = Stage.IDLE;
    private long startedAt;
    private long suppressUntil;

    Stage stage() {
        return stage;
    }

    boolean active() {
        return stage != Stage.IDLE;
    }

    boolean start(long tick) {
        if (active() || tick < suppressUntil) return false;
        stage = Stage.AXE;
        startedAt = tick;
        return true;
    }

    boolean expired(long tick) {
        return active() && tick - startedAt > 100;
    }

    void attacked(long tick) {
        if (stage != Stage.AXE) {
            throw new IllegalStateException("No active stun sequence");
        }
        stage = Stage.IDLE;
        suppressUntil = tick + 40;
    }

    void cancel() {
        stage = Stage.IDLE;
    }

    void reset() {
        cancel();
        suppressUntil = 0;
    }
}
