a9bsp
=====

The name "a9bsp" is short for Accessible Boolean Satisfiability Problem: the
ultimate goal of this library is to make satisfiability problems more
accessible to individuals without strong backgrounds in logical theory or
mathematics. Built on top of [pycosat](https://github.com/ContinuumIO/pycosat),
the library has straightforward, descriptive functions that generate equivalent
boolean satisfiability rules.

Examples
--------

### N-Queens Puzzle ###

The [N-queens puzzle](https://en.wikipedia.org/wiki/Eight_queens_puzzle) is a
puzzle in which the player attempts to place a number of queens, often 8, on a
board in such a way that none of the queens are in each other's line of attack.
Queens can attack pieces that are on the same row, column or diagonal.

Here is a programmatic description of the problem using a9bsp:

    from __future__ import print_function, division

    import itertools

    import a9bsp

    n_queens = a9bsp.AccessibleBSP()

    # Number of queens and board size; NxN board with N queens.
    queen_count = 8

    # Generate a chess board with each cell represented by an X and Y position.
    chess_board = itertools.product(range(queen_count), range(queen_count))

    # Define the conditions of the problem. Iterate through every square on the
    # board and compare it with every other square on the board.
    for (ax, ay), (bx, by) in itertools.combinations(chess_board, 2):

                                                # Two queens cannot:
        if ((ax == bx) or                       # - Be in the same column
            (ay == by) or                       # - Be in the same row
            (abs((ay - by) / (ax - bx)) == 1)): # - Be on the same diagonal

            # Therefore, two queens cannot be in any pairs of cells meeting
            # these conditions.
            n_queens.mutually_excludes([(ax, ay), (bx, by)])

    # One queen per column
    for row in range(queen_count):
        squares_in_column = [(n, row) for n in range(queen_count)]
        n_queens.includes_any(squares_in_column)

    # One queen per row
    for column in range(queen_count):
        squares_in_row = [(column, n) for n in range(queen_count)]
        n_queens.includes_any(squares_in_row)

    # Print a board with the positions of each queen
    for n, solution in enumerate(n_queens.solutions, 1):
        print("Solution %d:" % (n,))
        for y in range(queen_count):
            for x in range(queen_count):
                if (x, y) in solution:
                    print("Q ", end="")
                else:
                    print(". ", end="")
            print("")

The first solution of 92 produced by the script:

    Solution 1:
    . . Q . . . . .
    . . . . Q . . .
    . Q . . . . . .
    . . . . . . . Q
    . . . . . Q . .
    . . . Q . . . .
    . . . . . . Q .
    Q . . . . . . .
