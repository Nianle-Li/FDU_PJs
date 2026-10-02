package console.command;

import console.playground.PlayGround;

public class SelectGameCommand implements Command {
    private PlayGround session;

    public SelectGameCommand(PlayGround session) {
        this.session = session;
    }
    @Override
    public boolean canAccept(String input) {
        try {
            Integer.parseInt(input);
            return true;
        } catch (NumberFormatException e) {
            return false;
        }
    }
    @Override
    public void execute(String input) {
        session.activateGame(Integer.parseInt(input) - 1);
    }

    @Override
    public String prompt() {
        int min = 1; // 最小游戏编号
        int max = session.getGames().size(); // 最大游戏编号
        return String.format("游戏编号:(%d~%d)", min, max);
    }

    @Override
    public boolean isEnabled() {
        return session.getGames().size() > 0;
    }

}
