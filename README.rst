lithoxyl
========

logging, with a geological bent


Reasons to use Lithoxyl
-----------------------

* More specific: distinguishes between level and status
* Safer: Transactional logging ensures that exceptions are always recorded appropriately
* Lower overhead: Lithoxyl can be used more places in code (e.g., tight loops), as well as more environments, without concern of excess overhead.
* More Pythonic: Python's logging module is a port of log4j, and it shows.
* No global state: Lithoxyl has virtually no internal global state, meaning fewer gotchas overall
* Higher concurrency: less global state and less overhead mean fewer places where contention can occur
* More succinct: Rather than try/except/finally, use a simple with block
* More useful: Lithoxyl represents a balance between logging and profiling
* More composable: Get exactly what you want by recombining new and provided components
* More lightweight: Simplicity, composability, and practicality, make Lithoxyl something one might reach for earlier in the development process. Logging shouldn't be an afterthought, nor should it be a big investment that weighs down development, maintenance, and refactoring.
