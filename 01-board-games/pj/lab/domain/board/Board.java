package domain.board;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

public class Board {
    private final int size;
    private final PieceColor[][] grid;
    
    public Board(int size) {
        this.size = size;
        this.grid = new PieceColor[size][size];
    }

    public Board(PieceColor[][] grid) {
        this.grid = grid;
        this.size = grid.length;
    }

    /**
     * 替换或者放置棋子在指定位置
     */
    public void replacePiece(Location loc, PieceColor piece) {
        if (!isValidLocation(loc)) {
            throw new BoardException("无效的位置:" + loc);
        }
        grid[loc.getX()][loc.getY()] = piece;
    }

    /**
     * 在指定的空白位置放置棋子
     */
    public void placePiece(Location loc, PieceColor piece) {
        if (!isValidPlacement(loc)) {
            throw new BoardException("无效的位置:" + loc);
        }
        grid[loc.getX()][loc.getY()] = piece;
    }

    /**
     * 在指定位置放置指定颜色的棋子
     */
    public void placePiece(int x, int y, PieceColor piece) {
        placePiece(Location.of(x, y), piece);
    }

    public boolean isValidLocation(Location loc) {
        if (loc.getX() < 0 || loc.getX() >= size || loc.getY() < 0 || loc.getY() >= size) {
            return false;
        }
        return true;
    }

    public boolean isValidPlacement(Location loc) {
        if (!isValidLocation(loc))
            return false;
        if (getPiece(loc) != null) {
            return false;
        }
        return true;
    }

    public PieceColor getPiece(Location loc) {
        return getPiece(loc.getX(), loc.getY());
    }

    public PieceColor getPiece(int x, int y) {
        if (!isValidLocation(Location.of(x, y))) {
            throw new BoardException("无效的位置:" + Location.of(x, y));
        }
        return grid[x][y];
    }
    
    public int getSize() {
        return size;
    }

    /*
     * 注意：目前的实现方案会有性能问题，后面可以使用Iterator进行优化
     * 获取从指定位置开始，指定方向的连续的所有棋子(包含位置信息,不包含起始点)
     */
    public List<Piece> getLine(Location loc, Direction dir) {
        if (!isValidLocation(loc))
            throw new BoardException("无效的位置:" + loc);

        List<Piece> pieces = new ArrayList<>();

        Location nextLoc = loc.at(dir);

        while (isValidLocation(nextLoc)) {
            if (getPiece(nextLoc) != null) {
                pieces.add(new Piece(nextLoc, getPiece(nextLoc)));
            } else {
                break;
            }
            nextLoc = nextLoc.at(dir);
        }

        return pieces;
    }

    /*
     * 注意：目前的实现方案会有性能问题，后面可以使用Iterator进行优化
     * 获取棋盘上所有的棋子(包含位置信息)
     */
    public Piece[] getAll(boolean includeEmpty) {
        List<Piece> allPieces = new ArrayList<>();
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                if (includeEmpty)
                    allPieces.add(new Piece(i, j, grid[i][j]));
                else if (grid[i][j] != null)
                    allPieces.add(new Piece(i, j, grid[i][j]));
            }
        }
        return allPieces.toArray(new Piece[0]);
    }

    // 计算某种颜色棋子的数量
    public int getPieceCount(PieceColor color) {
        return (int) Stream.of(getAll(false))
                .filter(each -> each.getColor() == color)
                .count();
    }

    /**
     * 清空棋盘
     */
    public void clear() {
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                grid[i][j] = null;
            }
        }
    }
}
