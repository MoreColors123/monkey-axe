package infra;

import actor.Player;
import actor.Player.PlayerCharacter;
import static actor.Player.PlayerCharacter.*;
import static infra.Settings.*;
import java.awt.Color;
import java.awt.Graphics2D;
import scene.Ending;
import scene.Disclaimer;
import scene.Initializing;
import scene.Intro;
import scene.OLPresents;
import scene.OldMap;
import scene.Ranking;
import scene.SelectPlayer;
import scene.Stage;
import scene.WinnersDontUseDrugs;
import scene.Title;

/**
 * GoldenAxeGame class.
 * 
 * @author Leonardo Ono (ono.leo80@gmail.com)
 */
public class GoldenAxeGame {

    public static int numberOfPlayers = 1;
    
    public static PlayerCharacter characterPlayer1;
    public static PlayerCharacter characterPlayer2;

    public static Player player1;
    public static Player player2;
    
    public static int stage = 0;
    public static String stageId;
    
    public static int introIndex = 0;
    public static boolean showingDemo = false;
    // TESTING TOGGLES
    // When true, the title screen never fires the attract intro (title.ani's
    // show_intro event is ignored), so you stay on the title until 1P START.
    // Set to false to restore the normal attract flow (intro cutscene + demo).
    public static boolean SKIP_INTRO = true;
    // When true, every player state switch is printed to the console
    // (diagnosis aid; remove once done).
    public static boolean DEBUG_STATE_SWITCH = true;
    // When true, the game boots straight into Stage 1 as Guybrush, in action
    // (no OL Presents / disclaimer / winners screens, no title, no select
    // screen, no intro). Set to false to restore the normal flow.
    public static boolean TEST_BOOT_TO_GAME = true;
    public static PlayerCharacter demoCharacter = GUYBRUSH;
    public static int demoPotionsCount = 2;
    public static int demoStage = 100;
    
    
    public static void reset() {
        numberOfPlayers = 1;
        characterPlayer1 = null;
        characterPlayer2 = null;
        player1 = null;
        player2 = null;
        stage = 0;
        stageId = "";
        introIndex = -1;
        showingDemo = false;
    }

    public static void setNextDemoCharacter() {
        introIndex++;
        if (introIndex > 2) {
            return;
        }
        showingDemo = true;
        demoCharacter = PlayerCharacter.values()[introIndex];
        demoPotionsCount = Util.random(1, demoCharacter.maxPotions);
        demoStage = 100 + introIndex;
    }
    
    // ---
    
    private final SceneManager sceneManager = new SceneManager();
    
    public void start() {
        Audio.start();

        sceneManager.addState(new Initializing(sceneManager, this));
        sceneManager.addState(new OLPresents(sceneManager, this));
        sceneManager.addState(new Disclaimer(sceneManager, this));
        sceneManager.addState(new WinnersDontUseDrugs(sceneManager, this));
        sceneManager.addState(new Title(sceneManager, this));
        sceneManager.addState(new Intro(sceneManager, this));
        sceneManager.addState(new SelectPlayer(sceneManager, this));
        sceneManager.addState(new Stage(sceneManager, this));
        sceneManager.addState(new OldMap(sceneManager, this));
        sceneManager.addState(new Ending(sceneManager, this));
        sceneManager.addState(new Ranking(sceneManager, this));
        sceneManager.startAll();
        
        // TESTING: boot straight into the action (see TEST_BOOT_TO_GAME).
        if (TEST_BOOT_TO_GAME) {
            numberOfPlayers = 1;
            characterPlayer1 = GUYBRUSH;
            sceneManager.switchTo("stage");
        }
        else {
            sceneManager.switchTo("initializing");
        }
        //sceneManager.switchTo("ol_presents");
        //sceneManager.switchTo("title");
        //sceneManager.switchTo("intro");
        //sceneManager.switchTo("select_player");
        //sceneManager.switchTo("stage");
        //sceneManager.switchTo("old_map");
        //sceneManager.switchTo("ending");
        //sceneManager.switchTo("ranking");
    }
    
    public void update(long delta) {
        sceneManager.update(delta);
    }
    
    public void fixedUpdate() {
        Audio.update();
        sceneManager.fixedUpdate();
    }
    
    public void draw(Graphics2D g) {
        g.setBackground(Color.BLACK);
        g.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        sceneManager.draw(g);
    }

}
