package scene;

import static actor.Player.PlayerCharacter.GUYBRUSH;
import infra.GoldenAxeGame;
import infra.Input;
import infra.SceneManager;
import infra.State;
import infra.TextRenderer;
import java.awt.Graphics2D;
import java.awt.event.KeyEvent;

/**
 * TEST: stage-select prompt shown at boot. Type a stage number (1-9) and press
 * ENTER to jump straight to that stage as Guybrush. Enabled by
 * GoldenAxeGame.TEST_STAGE_SELECT.
 */
public class StageSelect extends State<GoldenAxeGame, SceneManager> {

    private String buffer = "";

    public StageSelect(SceneManager manager, GoldenAxeGame game) {
        super(manager, "stage_select", game);
    }

    @Override
    public void onEnter() {
        buffer = "";
    }

    private void startStage(int stage) {
        GoldenAxeGame.numberOfPlayers = 1;
        GoldenAxeGame.characterPlayer1 = GUYBRUSH;
        GoldenAxeGame.stage = stage - 1; // Stage.onEnter increments it
        manager.switchTo("stage");
    }

    @Override
    public void fixedUpdate() {
        for (int n = 1; n <= 9; n++) {
            if (Input.isKeyJustPressed(KeyEvent.VK_0 + n)) {
                buffer = String.valueOf(n);
            }
        }
        if (Input.isKeyJustPressed(KeyEvent.VK_BACK_SPACE)) {
            buffer = "";
        }
        if (Input.isKeyJustPressed(KeyEvent.VK_ENTER)) {
            int stage = buffer.isEmpty() ? 1 : Integer.parseInt(buffer);
            startStage(Math.max(1, Math.min(9, stage)));
        }
    }

    @Override
    public void draw(Graphics2D g) {
        TextRenderer.draw(g, "GUYBRUSH MOD - STAGE SELECT", 2, 4);
        TextRenderer.draw(g, "TYPE A STAGE NUMBER 1-9", 2, 6);
        TextRenderer.draw(g, "STAGE: " + (buffer.isEmpty() ? "-" : buffer), 2, 8);
        TextRenderer.draw(g, "ENTER = START    BACKSPACE = CLEAR", 2, 10);
    }

}
