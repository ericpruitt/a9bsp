#!/usr/bin/env python
import itertools

import pycosat


class Error(Exception):
    """
    Base exception class inherited by all a9bsp-specific exceptions.
    """


class UnsatisfiableConstraints(Error):
    """
    Exception raised when constraints are unsatisfiable.
    """


class SolutionNotFound(Error):
    """
    Exception raised when a solution could not be determined within the
    propagation limit.
    """


class AccessibleBSP:
    def __init__(self):
        self.clauses = list()
        self.e2id = dict()
        self.id2e = dict()
        self.variables = 0

    @property
    def dimacs_cnf(self):
        """
        Return representation of the boolean satisfiability problem in DIMACS
        conjunctive normal form.
        """
        lines = list()

        # Comments mapping numbers to hashables.
        for key, hashable in self.id2e.iteritems():
            lines.append("c %d = %r <%d>" % (key, hashable, hash(hashable)))

        # CNF clauses
        lines.append("p cnf %d %d" % (len(self.clauses), self.variables))
        for clause in self.clauses:
            lines.append(" ".join(map(str, clause)) + " 0")

        return "\n".join(lines) + "\n"

    def __str__(self):
        """
        Same as `AccessibleBSP.dimacs_cnf` but strips the trailing newline.
        """
        return self.dimacs_cnf[:-1]

    def to_id(self, element):
        """
        Return a number that should be used to represent the hashable `element`
        in the class's internal CNF clauses. If `element` has not previously
        been passed to this method, it will be assigned a new, unique ID that
        is then returned. Otherwise, the ID previously assigned to `element` is
        returned.
        """
        if element not in self.e2id:
            self.variables += 1
            self.e2id[element] = self.variables
            self.id2e[self.variables] = element

        return self.e2id[element]

    def from_id(self, eid):
        """
        Return the hashable represented by `eid` in the class's internal
        representation of the boolean satisfiability problem.
        """
        return self.id2e[eid]

    def remap_solution(self, solution):
        """
        Convert `solution` from numeric-CNF representation to set containing
        the user-given hashables represented by each.
        """
        return set((self.from_id(i) for i in solution if i > 0))

    def mutually_excludes(self, elements):
        """
        Assert that all members of `elements` are mutually exclusive in any
        solutions.
        """
        self.clauses.append([-self.to_id(e) for e in  elements])

    def includes(self, element):
        """
        Assert that valid solutions must contain `element`.
        """
        self.clauses.append([self.to_id(element)])

    def includes_all(self, elements):
        """
        Assert that valid solutions must contain all `elements`.
        """
        for element in elements:
            self.includes(element)

    def includes_any(self, elements, n=1):
        """
        Assert that valid solutions must contain at least one of `elements`.
        """
        elements = [self.to_id(i) for i in elements]
        element_len = len(elements)
        combination_length = element_len + 1 - n
        for combination in itertools.combinations(elements, combination_length):
            self.clauses.append(list(combination))

    def excludes(self, element):
        """
        Assert that valid solutions must exclude `element`.
        """
        self.clauses.append([-self.to_id(element)])

    def has_codependencies(self, elements):
        """
        Assert that all members of `elements` are codependent on one another.
        """
        for j, k in itertools.combinations(map(self.to_id, elements), 2):
            self.clauses.append([j, -k])
            self.clauses.append([-j, k])

    def has_dependencies(self, element, on=None, n=None):
        """
        Assert that if `element` is present in a solution, at least `n` members
        of `on` must also be present. When `n` is unspecified, all members of
        `on` are required.
        """
        eid = self.to_id(element)
        on = [self.to_id(i) for i in on]
        len_on = len(on)
        n = len_on if n is None else n

        for combination in itertools.combinations(on, len_on + 1 - n):
            self.clauses.append([-eid] + list(combination))

    @property
    def solution(self):
        """
        Return arbitrary solution to the currently described satisfiability
        problem.
        """
        solution = pycosat.solve(self.clauses)

        if solution == "UNSAT":
            raise UnsatisfiableConstraints("Constraints are unsatisfiable")
        elif solution == "UNKNOWN":
            raise SolutionNotFound("Search limits exhausted without solution")
        else:
            return self.remap_solution(solution)

    @property
    def minimal_solution(self):
        """
        Return solution to the least number of "true" variables. If multiple
        solutions have the same number of "true" variables, only one of them
        will be returned.
        """
        last = None
        for solution in self.solutions:
            if last is None or len(solution) < lastlen:
                last = solution
                # Nothing will be smaller than an empty solution.
                if not solution:
                    break

        return last

    @property
    def maximal_solution(self):
        """
        Return solution to the greatest number of "true" variables. If multiple
        solutions have the same number of "true" variables, only one of them
        will be returned.
        """
        last = None
        for solution in self.solutions:
            len_solution = len(solution)
            if last is None or len_solution > len(last):
                last = solution
                # Nothing will be larger than a solution with everything.
                if len_solution == self.variables:
                    break

        return last

    @property
    def solutions(self):
        """
        Yield each solution to the current set of constraints.
        """
        solution_found = False
        for solution in pycosat.itersolve(self.clauses):
            yield self.remap_solution(solution)
            solution_found = True

        if not solution_found:
            # Only present to raise a descriptive exception.
            self.solution

    def partition_solutions(self, max_group_size=None):
        """
        Return a list of non-intersecting solutions that, when united, include
        all elements that appear in any solution. This is useful when
        attempting to group elements into non-conflicting batches for further
        processing. The `max_group_size` parameter can be used to limit the
        size of each of the partitions. When unspecified, the size is
        unlimited.
        """
        # TODO: Add option that permits intersecting solutions.
        solutions = list()
        actually_had_solution = False
        for solution in pycosat.itersolve(self.clauses):
            actually_had_solution = True

            solset = frozenset((i for i in solution if i > 0))
            if max_group_size is None or len(solset) <= max_group_size:
                solutions.append(frozenset((i for i in solution if i > 0)))

        if not solutions:
            if actually_had_solution:
                raise ValueError("max_group_size excludes all solutions")
            else:
                # Only present to raise a descriptive exception.
                self.solution

        elif len(solutions) == 1:
            return [self.remap_solution(solutions[0])]

        else:
            target_pool_size = len(set().union(*solutions))
            solutions.sort(key=lambda x: -len(x))

        # Pruned depth-first search of a dynamically generated graph of the
        # potential combinations of solutions. [P]: Pruning is done by taking
        # advantage of a few simple rules:
        #
        # - A solution cannot be present in the list of solutions more than
        #   once.
        # - A solution should have no elements in common with any of the
        #   previously visited solutions (this is purpose of "pool" below).
        # - In line with the previous rule, the length of the next visited
        #   solution added to the length of all previously visited solutions
        #   has to be less than the total number of known variables.
        #
        # Ideally, this always finds the smallest number of solutions possible
        # to create a cohesive set of all members, but I am not sure if the
        # current implementation actually guarantees that.
        visted = set()
        for solution in solutions:
            stack = [(solution,)]
            graph = dict()

            while stack:
                vertex = stack.pop()

                # The graph is also the visitation history.
                if vertex not in graph:
                    if len(vertex) == 1:
                        edges = list()
                        candidates = solutions
                        pool = vertex[0]
                    else:
                        # Inherit edges and pool from parent node then update
                        # and prune respectively.
                        edges, pool = graph[vertex[:-1]]
                        pool = pool | vertex[-1]
                        candidates = [e[-1] for e in edges]

                    pool_size = len(pool)
                    max_size = target_pool_size - pool_size

                    for solution in candidates:
                        # Refer to [P] above.
                        if (len(solution) > max_size or solution in vertex
                          or solution & pool):
                            continue

                        new_vertex = vertex + (solution,)
                        if (pool_size + len(solution)) == target_pool_size:
                            return [self.remap_solution(s) for s in new_vertex]

                        # Edges should be traversed starting with the most
                        # desirable edge first.
                        edges.append(new_vertex)

                    graph[vertex] = (edges, pool)
                    stack.extend(edges)

        raise UnsatisfiableConstraints("Solutions could not be partitioned")
