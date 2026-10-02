package domain.game;

import domain.board.Board;
import domain.board.Location;
import domain.board.PieceColor;

public class PeaceGame implements Game {
    Board board;
    private boolean finished = false;
    private PieceColor currentPieceColor;

    public String getGameType() {
        return "peace";
    }

    public PeaceGame() {
        this.board = new Board(8);
        // 初始化棋盘中心4子，与黑白棋相同的布局
        board.placePiece(Location.of(3, 3), PieceColor.WHITE);
        board.placePiece(Location.of(3, 4), PieceColor.BLACK);
        board.placePiece(Location.of(4, 3), PieceColor.BLACK);
        board.placePiece(Location.of(4, 4), PieceColor.WHITE);
        currentPieceColor = PieceColor.BLACK;
    }

    public PeaceGame(Board board, PieceColor currentPieceColor) {
        this.board = board;
        this.currentPieceColor = currentPieceColor;
    }

    public boolean placePiece(Location loc) {
        if (finished) {
            throw new GameException("游戏已结束");
        }
        if (!board.isValidPlacement(loc)) {
            throw new GameException("无效位置:" + loc.toString());
        }
        board.placePiece(loc, currentPieceColor);
        currentPieceColor = currentPieceColor.oppositeColor();
        finished = isFinished();
        return true;
    }

    public Board getBoard() {
        return board;
    }

    private boolean isFinished() {
        return board.getAll(false).length == board.getSize() * board.getSize();
    }

    @Override
    public boolean isOver() {
        return finished;
    }

    public PieceColor getCurrentPlayer() {
        return currentPieceColor;
    }

    public PieceColor getWinner() {
        return null;
    }
}
