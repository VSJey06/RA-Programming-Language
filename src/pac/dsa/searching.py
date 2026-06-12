class SearchAlgos:
    @staticmethod
    def call(algo, arr, target):
        if algo == "linear":
            return SearchAlgos._linear(arr, target)
        elif algo == "binary":
            return SearchAlgos._binary(arr, target)
        else:
            return -1

    @staticmethod
    def _linear(arr, target):
        for i, val in enumerate(arr):
            if val == target:
                return i
        return -1

    @staticmethod
    def _binary(arr, target):
        arr_sorted = sorted(arr)  # binary requires sorted
        low, high = 0, len(arr_sorted)-1
        while low <= high:
            mid = (low+high)//2
            if arr_sorted[mid] == target:
                return mid
            elif arr_sorted[mid] < target:
                low = mid+1
            else:
                high = mid-1
        return -1