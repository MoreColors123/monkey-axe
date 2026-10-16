package infra;

import static infra.Settings.*;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.event.KeyEvent;
import java.util.ArrayList;
import java.util.List;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;

/**
 * Hidden cheat/debug menu overlay.
 *
 * Type the magic word "ape" anywhere to open it, and again (or press ESC) to
 * close it. While open the active scene is paused, so the menu keys cannot leak
 * into gameplay.
 *
 * This replaces the loose in-game cheat keys that used to sit directly in
 * {@code Stage} (Y auto-kill, G no-thieves, X mount). Only the switches worth
 * keeping are exposed here; the shipping pass removes the rest and the normal
 * boot (see HANDOFF.md §0/§14).
 *
 * @author Leonardo Ono (ono.leo80@gmail.com)
 */
public class CheatMenu {

    private static final String OPEN_SEQUENCE = "ape";
    private static final Color SELECTED_COLOR = Util.getColor("0xffe878");
    private static final Color ITEM_COLOR = Util.getColor("0xceefef");

    /** One row: a toggle (getter+setter) or an action (action). */
    private static final class Entry {
        final String label;
        final BooleanSupplier getter;
        final Consumer<Boolean> setter;
        final Runnable action;

        Entry(String label, BooleanSupplier getter
                , Consumer<Boolean> setter, Runnable action) {
            this.label = label;
            this.getter = getter;
            this.setter = setter;
            this.action = action;
        }

        boolean isToggle() {
            return getter != null;
        }
    }

    private final SceneManager sceneManager;
    private final List<Entry> entries = new ArrayList<>();
    private boolean open;
    private int selected;

    public CheatMenu(SceneManager sceneManager) {
        this.sceneManager = sceneManager;
        entries.add(new Entry("STAGE SELECT", null, null, this::openStageSelect));
        entries.add(new Entry("MOUNT BEAST", null, null, this::spawnMountBeast));
        entries.add(new Entry("AUTO-KILL ENEMIES"
                , () -> GoldenAxeGame.TEST_AUTO_KILL_ENEMIES
                , value -> GoldenAxeGame.TEST_AUTO_KILL_ENEMIES = value, null));
        entries.add(new Entry("NO THIEVES"
                , () -> GoldenAxeGame.TEST_NO_THIEVES
                , value -> GoldenAxeGame.TEST_NO_THIEVES = value, null));
        entries.add(new Entry("INVINCIBLE PLAYER"
                , () -> GoldenAxeGame.TEST_INVINCIBLE
                , value -> GoldenAxeGame.TEST_INVINCIBLE = value, null));
    }

    public boolean isOpen() {
        return open;
    }

    private void open() {
        open = true;
        selected = 0;
    }

    private void close() {
        open = false;
    }

    // Jump to the boot stage-select prompt; it takes over from here and starts
    // the chosen stage as Guybrush (see scene.StageSelect).
    private void openStageSelect() {
        close();
        sceneManager.switchTo("stage_select");
    }

    // Spawn a mountable beast resting beside the player, so beast mounting can
    // be tested without the (now shipped-away) Stage 1 test arena.
    private void spawnMountBeast() {
        if (sceneManager.getCurrentState() instanceof scene.Stage stage) {
            stage.spawnMountBeast();
            close();
        }
    }

    public void fixedUpdate() {
        if (Input.typedKeysEndWith(OPEN_SEQUENCE)) {
            Input.clearTypedKeys();
            if (open) {
                close();
            }
            else if (!sceneManager.isTransiting()) {
                open();
            }
            return;
        }
        if (!open) {
            return;
        }
        if (Input.isKeyJustPressed(KeyEvent.VK_UP)) {
            selected--;
            if (selected < 0) {
                selected = entries.size() - 1;
            }
        }
        else if (Input.isKeyJustPressed(KeyEvent.VK_DOWN)) {
            selected++;
            if (selected >= entries.size()) {
                selected = 0;
            }
        }
        else if (Input.isKeyJustPressed(KeyEvent.VK_ENTER)) {
            Entry entry = entries.get(selected);
            if (entry.isToggle()) {
                entry.setter.accept(!entry.getter.getAsBoolean());
            }
            else if (entry.action != null) {
                entry.action.run();
            }
        }
        else if (Input.isKeyJustPressed(KeyEvent.VK_ESCAPE)) {
            close();
        }
    }

    public void draw(Graphics2D g) {
        if (!open) {
            return;
        }
        g.setColor(new Color(0, 0, 0, 200));
        g.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        TextRenderer.draw(g, "CHEAT MENU", 13, 3);
        int row = 7;
        for (int i = 0; i < entries.size(); i++, row += 2) {
            Entry entry = entries.get(i);
            String text = (i == selected ? "> " : "  ") + entry.label;
            if (entry.isToggle()) {
                text += entry.getter.getAsBoolean() ? ": ON" : ": OFF";
            }
            TextRenderer.draw(g, text, 6, row
                    , i == selected ? SELECTED_COLOR : ITEM_COLOR);
        }
        TextRenderer.draw(g, "UP/DOWN  ENTER  ESC", 6, row + 2);
    }

}
