package domain.game;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

import domain.board.Board;
import domain.board.Direction;
import domain.board.Location;
import domain.board.Piece;
import domain.board.PieceColor;

public class ReversiGame implements Game {
    private final Board board;
    private boolean finished = false;
    private PieceColor winner = null;
    private PieceColor currentPieceColor;

    public ReversiGame() {
        this.board = new Board(8);
        // 初始化棋盘中心4子
        board.placePiece(Location.of(3, 3), PieceColor.WHITE);
        board.placePiece(Location.of(3, 4), PieceColor.BLACK);
        board.placePiece(Location.of(4, 3), PieceColor.BLACK);
        board.placePiece(Location.of(4, 4), PieceColor.WHITE);
        currentPieceColor = PieceColor.BLACK;
    }

    public ReversiGame(Board board, PieceColor currentPieceColor) {
        this.board = board;
        this.currentPieceColor = currentPieceColor;
    }

    @Override
    public String getGameType() {
        return "reversi";
    }
    
    @Override
    public List<String> getSupportedActions() {
        return List.of("pass");
    }
    
    @Override
    public boolean executeAction(String action, Object... params) {
        if ("pass".equals(action)) {
            return pass();
        }
        return Game.super.executeAction(action, params);
    }

    /**
     * 当前玩家在指定位置落子
     */
    public boolean placePiece(Location loc) {
        if (!board.isValidPlacement(loc))
            throw new GameException("非法位置:" + loc.toString());
        List<Piece> pieces = getPiecesAttactedBy(loc, currentPieceColor);
        if (pieces.isEmpty())
            throw new GameException("此处无可攻击的棋子:" + loc.toString());

        board.placePiece(loc, currentPieceColor);
        flipPieces(pieces);
        currentPieceColor = currentPieceColor.oppositeColor();
        if (checkFinished()) {
            winner = getWinner();
            finished = true;
        }
        return true;
    }

    /**
     * 当前玩家跳过回合
     */
    public boolean pass() {
        if (!shouldPass())
            throw new GameException("此处不能跳过");
        currentPieceColor = currentPieceColor.oppositeColor();
        return true;
    }

    /**
     * 判断当前玩家是否需要跳过回合（无法落子）
     */
    public boolean shouldPass() {
        return getAllValidLocation(currentPieceColor).isEmpty();
    }

    /**
     * 判断指定位置是否可以落子
     */
    private boolean isValidPlace(Location location, PieceColor pieceColor) {
        return !getPiecesAttactedBy(location, pieceColor).isEmpty();
    }

    /**
     * 获取可以被翻转的对方棋子
     * 返回在指定方向上被夹住的连续对方棋子
     */
    private List<Piece> getAttactedPieces(PieceColor pieceColor, List<Piece> pieces) {

        List<Piece> affectedPieces = new ArrayList<>();
        PieceColor oppositeColor = pieceColor.oppositeColor();

        for (Piece piece : pieces) {
            if (piece.getColor() == oppositeColor) {
                affectedPieces.add(piece);
            } else if (piece.getColor() == pieceColor) {
                return affectedPieces;
            } else {
                return new ArrayList<>();
            }
        }
        return new ArrayList<>();
    }

    /**
     * 获取所有会被翻转的对方棋子
     * 检查所有方向上被夹击的棋子
     */
    private List<Piece> getPiecesAttactedBy(Location location, PieceColor pieceColor) {
        return Stream.of(Direction.getAllDirections())
                .map(dir -> getAttactedPieces(
                        pieceColor,
                        board.getLine(location, dir)))
                .flatMap(List::stream)
                .toList();
    }

    /**
     * 翻转指定的棋子
     */
    public void flipPieces(List<Piece> pieces) {
        for (Piece piece : pieces) {
            board.replacePiece(
                    piece.getLocation(),
                    piece.getColor().oppositeColor());
        }
    }

    /**
     * 获取棋盘
     */
    public Board getBoard() {
        return board;
    }

    /**
     * 获取指定颜色玩家可以落子的所有位置
     */
    public List<Location> getAllValidLocation(PieceColor piece) {
        return Stream.of(board.getAll(true))
                .filter(each -> !each.isOccupied())
                .filter(each -> isValidPlace(each.getLocation(), piece))
                .map(each -> each.getLocation())
                .toList();
    }

    /**
     * 计算某种颜色的棋子数量
     */
    public int getPieceCount(PieceColor piece) {
        return board.getPieceCount(piece);
    }

    /**
     * 检查游戏是否结束
     * 棋盘填满或双方都无法落子时游戏结束
     */
    public boolean checkFinished() {
        if (this.board.getAll(false).length == 64)
            return true;
        for (PieceColor pieceColor : PieceColor.allColors()) {
            if (!getAllValidLocation(pieceColor).isEmpty())
                return false;
        }
        return true;
    }

    /**
     * 获取胜利者
     * 游戏结束时棋子数量多的一方获胜
     */
    public PieceColor getWinner() {
        // 游戏结束，并且棋子多的一方获胜
        if (finished) {
            if (getPieceCount(PieceColor.BLACK) > getPieceCount(PieceColor.WHITE))
                return PieceColor.BLACK;
            else
                return PieceColor.WHITE;
        }
        return null;
    }

    public PieceColor getCurrentPlayer() {
        return currentPieceColor;
    }

    public boolean isOver() {
        return finished;
    }

    public PieceColor getWinnerColor() {
        return winner;
    }

    @Override
    public Integer getPlayerScore(PieceColor playerColor) {
        return getPieceCount(playerColor);
    }

    @Override
    public boolean canCurrentPlayerPass() {
        return shouldPass();
    }

    @Override
    public List<Location> getCurrentPlayerValidMoves() {
        return getAllValidLocation(currentPieceColor);
    }
}