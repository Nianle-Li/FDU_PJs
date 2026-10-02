package console.screen;

import domain.board.Location;

public class RawScreen implements Screen {
    private int rows;
    private int cols;
    private char[][] buffer;
    private int maxRow = -1;
    private int maxCol = -1;

    public RawScreen(int rows, int cols) {
        this.rows = rows;
        this.cols = cols;
        this.buffer = new char[rows][cols];
        clear();
    }

    // 动态扩容buffer
    private void ensureCapacity(int minRows, int minCols) {
        if (minRows <= rows && minCols <= cols) return;
        int newRows = Math.max(rows, minRows);
        int newCols = Math.max(cols, minCols);
        char[][] newBuffer = new char[newRows][newCols];
        for (int i = 0; i < rows; i++) {
            System.arraycopy(buffer[i], 0, newBuffer[i], 0, cols);
        }
        // 新增部分初始化为空格
        for (int i = rows; i < newRows; i++) {
            for (int j = 0; j < newCols; j++) {
                newBuffer[i][j] = ' ';
            }
        }
        for (int i = 0; i < rows; i++) {
            for (int j = cols; j < newCols; j++) {
                newBuffer[i][j] = ' ';
            }
        }
        buffer = newBuffer;
        rows = newRows;
        cols = newCols;
    }

    // 设置指定位置的字符
    @Override
    public void print(int row, int col, char c) {
        if (row < 0 || col < 0) return;
        ensureCapacity(row + 1, col + 1);
        buffer[row][col] = c;
        if (c != ' ') {
            if (row > maxRow) maxRow = row;
            if (col > maxCol) maxCol = col;
        }
    }

    // 设置指定位置开始的一串字符串
    @Override
    public void print(int row, int col, String s) {
        if (row < 0) return;
        ensureCapacity(row + 1, col + s.length());
        for (int i = 0; i < s.length(); i++) {
            int c = col + i;
            if (c >= 0) {
                buffer[row][c] = s.charAt(i);
                if (s.charAt(i) != ' ') {
                    if (row > maxRow) maxRow = row;
                    if (c > maxCol) maxCol = c;
                }
            }
        }
    }

    // 清屏
    public void clear() {
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                buffer[i][j] = ' ';
            }
        }
        maxRow = -1;
        maxCol = -1;
    }

    // 只显示输出了内容的部分
    public void outputToConsole() {
        for (int i = 0; i <= maxRow; i++) {
            for (int j = 0; j <= maxCol; j++) {
                System.out.print(buffer[i][j]);
            }
            System.out.println();
        }
    }

    public int getRows() {
        return rows;
    }

    public int getCols() {
        return cols;
    }

    public Screen offset(int rowOffset, int colOffset) {
        return new OffsetScreen(this, rowOffset, colOffset);
    }

    public Screen offset(Location loc) {
        return offset(loc.getX(), loc.getY());
    }

    public int getMaxCol() {
        return maxCol;
    }

    public int getMaxRow() {
        return maxRow;
    }
}