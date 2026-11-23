package com.maceassistant.modules;

/** Dependency-free regression test: compile with StunSequence.java and run main. */
public final class StunSequenceTest {
    public static void main(String[] args) {
        StunSequence sequence = new StunSequence();
        check(!sequence.active(), "Initially idle");
        check(sequence.start(100), "Blocking target starts sequence");
        check(sequence.stage() == StunSequence.Stage.SPEAR, "Spear must be first");
        check(!sequence.start(120), "Shield updates must not restart pending sequence");
        sequence.attacked(125);
        check(sequence.stage() == StunSequence.Stage.AXE, "Spear attack must advance to axe");
        check(!sequence.start(126), "Do not repeat spear between attacks");
        sequence.attacked(150);
        check(!sequence.active(), "Axe completes sequence");
        check(!sequence.start(189), "Suppress repeat attempts for 40 ticks");
        check(sequence.start(190), "Allow retry after suppression");
        check(!sequence.expired(290), "Timeout boundary");
        check(sequence.expired(291), "Timeout counts from sequence start");
        sequence.cancel();
        check(!sequence.active(), "Cancellation clears pending attack");
        check(sequence.start(300), "Start after cancellation");
        sequence.attacked(301);
        sequence.cancel();
        check(sequence.start(302), "Target change restarts at spear, never axe");
        check(sequence.stage() == StunSequence.Stage.SPEAR, "Restart must use spear");
        sequence.attacked(303);
        sequence.attacked(304);
        sequence.reset();
        check(sequence.start(0), "New session resets old tick suppression");
        sequence.reset();
        boolean rejected = false;
        try {
            sequence.attacked(0);
        } catch (IllegalStateException expected) {
            rejected = true;
        }
        check(rejected, "Idle cannot advance");
        System.out.println("PASS: spear -> axe order, suppression, timeout, cancellation, session reset");
    }

    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
}
