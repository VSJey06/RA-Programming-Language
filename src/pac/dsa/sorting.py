class SortingAlgos:
    @staticmethod
    def call(algo, arr):
        if algo == "bubble":
            return SortingAlgos._bubble(arr)
        elif algo == "quick":
            return SortingAlgos._quick(arr)
        elif algo == "merge":
            return SortingAlgos._merge(arr)
        else:
            return arr

    @staticmethod
    def _bubble(arr):
        a = list(arr)
        n = len(a)
        for i in range(n):
            for j in range(0, n-i-1):
                if a[j] > a[j+1]:
                    a[j], a[j+1] = a[j+1], a[j]
        return a

    @staticmethod
    def _quick(arr):
        if len(arr) <= 1:
            return arr
        pivot = arr[0]
        left = [x for x in arr[1:] if x <= pivot]
        right = [x for x in arr[1:] if x > pivot]
        return SortingAlgos._quick(left) + [pivot] + SortingAlgos._quick(right)

    @staticmethod
    def _merge(arr):
        if len(arr) <= 1:
            return arr
        mid = len(arr)//2
        left = SortingAlgos._merge(arr[:mid])
        right = SortingAlgos._merge(arr[mid:])
        i=j=k=0
        res = []
        while i < len(left) and j < len(right):
            if left[i] < right[j]:
                res.append(left[i]); i+=1
            else:
                res.append(right[j]); j+=1
        res.extend(left[i:])
        res.extend(right[j:])
        return res