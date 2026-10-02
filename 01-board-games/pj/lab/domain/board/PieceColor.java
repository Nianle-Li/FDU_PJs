package domain.board;

public enum PieceColor {
    BLACK,
    WHITE,
    BARRIER,
    BOMB_CRATER;  // 添加弹坑类型

    public PieceColor oppositeColor() {
        if (this == BLACK)
            return WHITE;
        else if (this == WHITE)
            return BLACK;
        else
            return this;  // 障碍物和弹坑没有对立色
    }

    public static PieceColor[] allColors() {
        return new PieceColor[] {BLACK, WHITE};  // 障碍物和弹坑不属于玩家颜色
    }

    @Override
    public String toString() {
        if(this == BLACK) return "●";
        else if(this == WHITE) return "○";
        else if(this == BARRIER) return "#";
        else return "@";  // 弹坑显示为@
    }
}