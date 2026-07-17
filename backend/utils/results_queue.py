"""Bounded top-N priority queue for accumulating prediction results.

Avoids repeatedly sorting a growing list of all predictions by keeping
only the top `max_size` by interaction_probability in a min-heap.
"""
import heapq


class BoundedResultsQueue:
    """
    A bounded priority queue that keeps only the top N results,
    avoiding the need to sort large lists repeatedly.
    """
    def __init__(self, max_size: int = 25):
        self.max_size = max_size
        self.heap = []  # Min heap (smallest at top)
        self.counter = 0  # Tiebreaker for equal scores

    def add_results(self, new_results):
        """Add multiple results efficiently"""
        for result in new_results:
            score = result["score"]["interaction_probability"]

            if len(self.heap) < self.max_size:
                # Heap not full, just add
                heapq.heappush(self.heap, (score, self.counter, result))
                self.counter += 1
            elif score > self.heap[0][0]:  # Better than worst result
                # Replace worst result
                heapq.heapreplace(self.heap, (score, self.counter, result))
                self.counter += 1

    def get_top_results(self):
        """Get results sorted by score (highest first)"""
        return [result for score, counter, result in sorted(self.heap, reverse=True)]

    def size(self):
        return len(self.heap)
