package domain.board;

public enum Direction {
    UP(-1, 0),
    DOWN(1, 0),
    LEFT(0, -1),
    RIGHT(0, 1),
    UP_LEFT(-1, -1),
    UP_RIGHT(-1, 1),
    DOWN_LEFT(1, -1),
    DOWN_RIGHT(1, 1);

    private final int dx;
    private final int dy;

    Direction(int dx, int dy) {
        this.dx = dx;
        this.dy = dy;
    }

    public int getDx() {
        return dx;
    }

    public int getDy() {
        return dy;
    }

    // 获取所有方向的列表
    public static Direction[] getAllDirections() {
        return Direction.values();
    }

    // 获取所有相反方向的方向对
    public static Direction[][] getOppositeDirections() {
        return new Direction[][] {
                { UP, DOWN },
                { LEFT, RIGHT },
                { UP_LEFT, DOWN_RIGHT },
                { UP_RIGHT, DOWN_LEFT }
        };
    }
}

