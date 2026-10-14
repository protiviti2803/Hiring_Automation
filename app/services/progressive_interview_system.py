import heapq
import uuid

class MaxPriorityQueue:
    """
    A Max-Priority Queue implementation using heapq (which is a min-heap by default).
    Priorities are negated to achieve max-heap behavior.
    Supports O(1) removals and updates by mapping item IDs to heap entries.
    Supports a O(N) min-priority eviction when clamping the size.
    """
    def __init__(self):
        self._heap = []
        self._entry_finder = {}  # maps item_id -> heap entry
        self.REMOVED = '<removed-item>'

    def push(self, item_id, priority, item_data):
        """Pushes an item with a given priority (frequency). Updates existing item if present."""
        if item_id in self._entry_finder:
            self.remove(item_id)
        # Negate priority to make it a Max-Priority Queue using a min-heap
        entry = [-priority, item_id, item_data]
        self._entry_finder[item_id] = entry
        heapq.heappush(self._heap, entry)

    def remove(self, item_id):
        """Marks an existing item as removed (lazy deletion)."""
        entry = self._entry_finder.pop(item_id, None)
        if entry:
            entry[-1] = self.REMOVED

    def pop_max(self):
        """Pops and returns the highest priority item. Returns (item_id, priority, item_data)."""
        while self._heap:
            neg_priority, item_id, item_data = heapq.heappop(self._heap)
            if item_data is not self.REMOVED:
                del self._entry_finder[item_id]
                return item_id, -neg_priority, item_data
        raise IndexError("pop from an empty priority queue")

    def pop_min(self):
        """
        Pops and returns the lowest priority item (used for eviction).
        Iterates over the heap in O(N) to find the minimum priority item, marks it removed, and returns it.
        """
        valid_entries = [entry for entry in self._heap if entry[-1] is not self.REMOVED]
        if not valid_entries:
            raise IndexError("pop from an empty priority queue")
        
        # Negated priority means the lowest priority has the largest negated value.
        # Find the entry with the maximum negated priority (which is the lowest frequency)
        min_entry = max(valid_entries, key=lambda x: x[0])
        item_id = min_entry[1]
        priority = -min_entry[0]
        item_data = min_entry[2]
        
        self.remove(item_id)
        self._prune_heap()
        return item_id, priority, item_data

    def _prune_heap(self):
        """Rebuilds the heap to discard deleted placeholders if they occupy more than half the heap."""
        if len(self._heap) > 2 * len(self._entry_finder):
            self._heap = [entry for entry in self._heap if entry[-1] is not self.REMOVED]
            heapq.heapify(self._heap)

    def get_all_sorted(self):
        """Returns all valid items in sorted order (highest priority first) without modifying the queue."""
        valid_entries = [entry for entry in self._heap if entry[-1] is not self.REMOVED]
        # Sort by neg_priority ascending -> priority descending
        sorted_entries = sorted(valid_entries, key=lambda x: x[0])
        return [(entry[1], -entry[0], entry[2]) for entry in sorted_entries]

    def clear(self):
        """Clears the queue."""
        self._heap.clear()
        self._entry_finder.clear()

    def __contains__(self, item_id):
        return item_id in self._entry_finder

    def __len__(self):
        return len(self._entry_finder)


class ProgressiveInterviewSystem:
    def __init__(self):
        # Core Data Structures
        self.pq1 = MaxPriorityQueue()  # Session Queue (Max size: 15)
        self.pq2 = MaxPriorityQueue()  # Database Queue (Unlimited size)
        self.frequency_registry = {}  # HashMap: question_id -> overall ask_count (int)

    def initialize_system(self, excel_data: list):
        """
        Initializes the system with database questions from Excel data.
        Populates the frequency registry and the PQ2 queue (Database Queue).
        
        excel_data parameter format:
        List of dicts, e.g.:
        [
            {"question_id": "q1", "question_text": "...", "category": "...", "frequency": 5},
            {"question_text": "...", "category": "..."}  # id will be generated automatically
        ]
        """
        self.pq1.clear()
        self.pq2.clear()
        self.frequency_registry.clear()

        for index, item in enumerate(excel_data):
            q_text = item.get("question_text", "").strip()
            if not q_text:
                continue

            q_id = item.get("question_id") or item.get("id") or f"q_{uuid.uuid4().hex[:8]}_{index}"
            q_category = item.get("category") or "Technical"
            q_frequency = int(item.get("frequency") or item.get("frequency_count") or 1)

            question_data = {
                "question_id": q_id,
                "question_text": q_text,
                "category": q_category
            }

            # Map in HashMap
            self.frequency_registry[q_id] = q_frequency
            
            # Push into PQ2 (Database Queue)
            self.pq2.push(q_id, q_frequency, question_data)

    def fetch_interview_questions(self, target_count: int) -> list:
        """
        Fetches dynamic questions for the upcoming interview.
        Validates target_count is between 5 and 15.
        Pulls from PQ1 first, then fills the remaining balance with highest-frequency questions from PQ2.
        
        Returns:
            list: List of question dictionaries.
        """
        # Validate target_count range constraint (5-15)
        if not isinstance(target_count, int) or not (5 <= target_count <= 15):
            raise ValueError(f"Interview question count must be between 5 and 15 inclusive. Received: {target_count}")

        selected_questions = []
        selected_ids = set()

        # 1. Pull as many questions as available from PQ1 (Session Queue) ordered by frequency first
        pq1_sorted = self.pq1.get_all_sorted()
        for q_id, priority, q_data in pq1_sorted:
            if len(selected_questions) >= target_count:
                break
            selected_questions.append(q_data)
            selected_ids.add(q_id)

        # 2. If balance needed, pull highest-frequency questions from PQ2 (Database Queue)
        if len(selected_questions) < target_count:
            pq2_sorted = self.pq2.get_all_sorted()
            for q_id, priority, q_data in pq2_sorted:
                if len(selected_questions) >= target_count:
                    break
                # Skip duplicate questions that were already pulled from PQ1
                if q_id not in selected_ids:
                    selected_questions.append(q_data)
                    selected_ids.add(q_id)

        return selected_questions

    def post_interview_update(self, asked_questions_list: list):
        """
        Updates frequencies post-interview.
        Frequencies are incremented in the HashMap registry.
        Questions are then pushed or updated in PQ1.
        If PQ1 exceeds the limit of 15 questions, the lowest frequency question is evicted.
        
        asked_questions_list parameter format:
        List of question dicts, e.g.:
        [
            {"question_id": "q1", "question_text": "...", "category": "..."},
            ...
        ]
        """
        for question in asked_questions_list:
            q_id = question.get("question_id")
            if not q_id:
                continue

            q_text = question.get("question_text", "")
            q_category = question.get("category", "Technical")

            # 1. Increment frequency registry
            current_frequency = self.frequency_registry.get(q_id, 0) + 1
            self.frequency_registry[q_id] = current_frequency

            # Also update priority in PQ2 if present in the database registry
            # (Ensures future runs use updated database frequencies)
            question_data = {
                "question_id": q_id,
                "question_text": q_text,
                "category": q_category
            }
            self.pq2.push(q_id, current_frequency, question_data)

            # 2. Push/Update question in PQ1 (Session Queue) with the updated priority
            self.pq1.push(q_id, current_frequency, question_data)

        # 3. Dynamic Eviction: if PQ1 size > 15, evict the lowest-frequency questions
        while len(self.pq1) > 15:
            evicted_id, evicted_priority, evicted_data = self.pq1.pop_min()
            # Note: We keep the item in the overall registry (HashMap) and PQ2,
            # but it is evicted from the active Session Queue (PQ1) to make room.
