package console.command;

import domain.game.ReversiGame;

public class PassCommand implements Command {

    private final ReversiGame game;

    public PassCommand(ReversiGame game) {
        this.game = game;
    }
    @Override
    public void execute(String string) {
        game.pass();
    }

    @Override
    public boolean canAccept(String input) {
        return input.equals("pass");
    }

    @Override
    public String prompt() {
        return "放弃行棋子(pass)";
    }

    @Override
    public boolean isEnabled() {
        return game.shouldPass() && !game.isOver();
    }

}

