###### Common Patterns

# Greedy & Bin Packing

When local optimization leads to global solutions — greedy strategies, bin packing heuristics, and the tradeoffs interviewers expect you to reason about.

Problems involving resource allocation, scheduling, interval management, and bin packing are natural fits for multi-file coding challenges because they're easy to state but surprisingly tricky to get right. This almost always leads us to greedy algorithms as a candidate solution. The part that makes them interesting interview material is the tradeoff between correctness and speed: a greedy approach runs fast, but does it actually give you the right answer?

Interviewers are not testing whether you've memorized the a problem from your algorithms class. They want to see you reason about *why* a greedy approach works for a given problem, or catch when it doesn't. The AI will happily generate a greedy solution for almost anything you throw at it. Your job is to know when that's correct and when it's dangerously wrong.

You don't need deep prior expertise with greedy algorithms going into these interviews. Interviewers expect you to assimilate the core ideas quickly and apply them to unfamiliar problems. What matters is your reasoning process, not whether you've seen the exact problem before.

## Recognizing the pattern

Greedy is the trickiest pattern to recognize because the *opportunity* is everywhere and the *correctness* is conditional. Almost any optimization problem looks like it might submit to a greedy solution — make the locally best choice and hope it works out. The skill is knowing when "hope" is enough and when you need to actually verify.

Tells that greedy is worth considering:

* **An optimization goal with a natural ordering.** Maximum non-overlapping intervals (order by end time), minimum bins (order by size), shortest job first. If the items have an obvious sort key, greedy is in the candidate set.
* **The choice at step k doesn't constrain step k+1.** Or at least, doesn't constrain it much. If picking the "best" thing now doesn't paint you into a corner later, greedy probably works.
* **Resource allocation, scheduling, interval management, packing.** These domains have a long history of clean greedy solutions, and interviewers love them for the same reason.

But greedy is also the pattern most likely to be *plausibly wrong*. The AI will happily produce a greedy solution to a problem where greedy gives the wrong answer — and the code will compile, run, and pass the test cases the interviewer gave you. So when you recognize a possibly-greedy problem, the immediate next move is to verify the greedy choice property holds, not to ship the code.

Ask three diagnostic questions before committing:

1. **Can I make a choice and never need to undo it?** If not, greedy won't work.
2. **After making one choice, does the remaining problem look like a smaller version of the same thing?** If not, optimal substructure doesn't hold.
3. **Can I construct a small counterexample where greedy gives the wrong answer?** If yes, you've just proved greedy is wrong. If you can't find one after a couple of minutes, greedy is *probably* fine, but that's not a proof.

## The greedy paradigm

The idea behind greedy algorithms is to make the choice that looks best at each step and never look back, with no backtracking or reconsidering. You commit to each local decision and hope (or prove) that the sequence of locally optimal choices leads to a globally optimal solution.

This works when two properties hold:

1. The greedy choice property holds — making the locally optimal choice doesn't prevent you from finding the globally optimal solution. In other words, you never need to undo a decision.
2. The problem has optimal substructure — after making a greedy choice, the remaining problem is a smaller instance of the same type of problem.

When both hold, greedy gives you the optimal answer and usually runs much faster than alternatives like dynamic programming. When either fails, greedy gives you something that *looks* reasonable but might be arbitrarily far from optimal.

Intuitively, you're usually going to disprove a greedy approach by counterexample than create a rigorous mathematical proof of these two properties. So being able to go "aha, if I make that choice first, then I'll miss the optimal solution in this way" is how most engineers will reason through whether greedy applies or not. Don't get hung up on a formal proof!

### An example: coin change

Consider making change for 36 cents with coins of denominations 25, 10, 5, and 1. The greedy approach picks the largest coin that fits at each step: 25, then 10, then 1. Three coins total. And that happens to be optimal.

![](../img/aicoding--patterns--greedy-algorithms/inline1.svg)

But change the denominations to 1, 3, and 4 and try making 6 cents. Greedy picks 4, then 1, then 1 which is three coins. The optimal answer is 3 + 3, just two coins. The greedy choice property doesn't hold here because picking the largest coin first backed us into a corner so we can disprove it with a counterexample.

## Interval scheduling

Interval scheduling is probably the most common greedy pattern you'll see. Given a set of intervals (meetings, tasks, jobs), select the maximum number of non-overlapping intervals, or find the minimum number of resources to handle all of them.

If you've seen interval questions before you know the answer: sort intervals by end time, then greedily pick the earliest-ending interval that doesn't overlap with your last selection. This works because choosing the interval that finishes earliest leaves the most room for future intervals.

![](../img/aicoding--patterns--greedy-algorithms/inline2.svg)

Sort by end time, then walk through: pick A (ends at 3), skip B and C (overlap), skip D (overlaps), pick E (starts at 4, ends at 7), pick F (starts at 7) which yields us three intervals selected, which is the maximum.

Maximum Non-Overlapping Intervals

```
def max_non_overlapping(intervals):
    intervals.sort(key=lambda x: x[1])
    selected = []
    last_end = float('-inf')

    for start, end in intervals:
        if start >= last_end:
            selected.append((start, end))
            last_end = end

    return selected
```

The time complexity is O(n log n) for the sort, then O(n) for the scan. This is one of those patterns where the greedy proof is clean and well-known, so if you or your AI produces this approach, you can be confident it's correct.

A closely related variant asks for the *minimum number of rooms* (or machines, or servers) to handle all intervals. That's a different problem with a different greedy strategy. You track active intervals and count the maximum overlap at any point.

Minimum Rooms (Meeting Rooms II)

```
import heapq

def min_rooms(intervals):
    if not intervals:
        return 0

    intervals.sort(key=lambda x: x[0])
    heap = []

    for start, end in intervals:
        if heap and heap[0] <= start:
            heapq.heapreplace(heap, end)
        else:
            heapq.heappush(heap, end)

    return len(heap)
```

The trick here is maintaining a min-heap of end times for currently active intervals. When a new interval starts after the earliest ending one, you reuse that room. Otherwise you need a new room. This is O(n log n) and is a completely different greedy strategy from the max-non-overlapping version above. In spite of being about the same shape, they actually have very different solutions.

## Bin packing

Got it so far? Let's ramp up the complexity a bit. Bin packing is where greedy gets really practical. You have items of various sizes and bins of fixed capacity and need to pack all items into as few bins as possible and this could be anything: allocating containers to servers, fitting tasks into time slots, memory management, even distributing load across worker nodes.

The bad news is that optimal bin packing is NP-hard (which makes it a perfect AI coding question!). The good news is that greedy heuristics get surprisingly close to optimal, and in an interview context, that's usually what's being asked for. You'll start with a greedy baseline and then make incremental optimizations as the problem allows.

### The main strategies

So what can we do? There's a few main strategies to consider, starting with the most naive:

**First-Fit**: For each item, scan bins from left to right and place the item in the first bin that has room. Simple and fast.

**Best-Fit**: For each item, place it in the bin where it fits most tightly (least remaining space after placement). Slightly better packing, slightly more work to find the right bin.

The problem with both of these is that they often lead to fragmented bins where you fill the bin with small items and then have nowhere to put the big ones.

**First-Fit Decreasing (FFD)**: Sort items largest-first, then apply First-Fit.

What we're doing here is trying to greedily place our biggest items first, because we know intuitively that we'll be able to find room for the smaller items. This is probably the strategy you used if you needed to move your belongings between apartments.

![](../img/aicoding--patterns--greedy-algorithms/inline3.svg)

FFD has a proven worst-case guarantee: it never uses more than (11/9) \* OPT + 6/9 bins, where OPT is the optimal number. In practice, it usually does better than that. No interviewer is going to quiz you on this exact guarantee, but knowing that it exists is a helpful thing to have in your back pocket.

First-Fit Decreasing Bin Packing

```
def first_fit_decreasing(items, bin_capacity):
    items_sorted = sorted(items, reverse=True)
    bins = []

    for item in items_sorted:
        placed = False
        for i, current_load in enumerate(bins):
            if current_load + item <= bin_capacity:
                bins[i] += item
                placed = True
                break

        if not placed:
            bins.append(item)

    return len(bins), bins
```

This runs in  in the worst case (n items, each scanning all existing bins). You can improve it to O(n log n) with a balanced BST or heap to track bin remaining capacities, but the  version is totally fine for an interview unless the problem explicitly requires better.

In an interview, if you're asked a bin packing variant, state the approach clearly. Say that you'll sort items in decreasing order and use first-fit, which gives a guaranteed approximation ratio. This shows you understand it's a heuristic and aren't claiming it's optimal. Interviewers appreciate that nuance. Follow this up with a simple benchmark (AI is really good at hammering these out!) and then you can optimize it further where needed.

### Real-world framing

Interview problems rarely say "solve bin packing." Instead they're dressed up as practical scenarios:

* **Server allocation**: You have N tasks with memory requirements and servers with fixed RAM. Minimize the number of servers.
* **Container packing**: Ship items in boxes of fixed volume. Minimize boxes used.
* **Job scheduling with deadlines**: Assign jobs to machines where each machine has a capacity per time window.
* **Disk partition management**: Files of various sizes need to go onto fixed-size partitions.

The translation step is part of what's being tested. Recognizing that "minimize the number of servers needed" is just bin packing in disguise is valuable, and it's something the AI might not explicitly tell you. Even being able to use the language "hey this looks like a bin packing problem" is a strong signal, so long as you're right.

### Multi-dimensional bin packing

Things get trickier when items have multiple dimensions. A server might have both CPU and memory limits. A shipping box has length, width, and height. In these cases, simple one-dimensional heuristics don't directly apply, and the problem becomes significantly harder.

The good approach for interviews is to reduce multi-dimensional packing to a series of one-dimensional decisions where possible. For instance, if servers have both CPU and memory, you could pack by the "tighter" or more constrained resource first (the one that will run out sooner) and check the other constraint as a feasibility filter. It's practical rather than optimal, and stating the tradeoff explicitly shows maturity.

2D First-Fit Decreasing (CPU + Memory)

```
def first_fit_decreasing_2d(items, cpu_cap, mem_cap):
    items_sorted = sorted(items, key=lambda x: max(x[0]/cpu_cap, x[1]/mem_cap), reverse=True)
    bins_cpu = []
    bins_mem = []

    for cpu, mem in items_sorted:
        placed = False
        for i in range(len(bins_cpu)):
            if bins_cpu[i] + cpu <= cpu_cap and bins_mem[i] + mem <= mem_cap:
                bins_cpu[i] += cpu
                bins_mem[i] += mem
                placed = True
                break

        if not placed:
            bins_cpu.append(cpu)
            bins_mem.append(mem)

    return len(bins_cpu)
```

The sort key here uses the maximum normalized resource demand, essentially asking "which dimension of this item is proportionally largest relative to capacity?" That's a reasonable heuristic, though there are others. Remember, the point isn't to memorize this.

Interviewers don't expect you to have multi-dimensional bin packing algorithms memorized. What they want to see is that you can take a known technique, adapt it to new constraints, and clearly communicate what guarantees you're giving up. Saying "this is a heuristic and I'm not certain it's optimal" is exactly right.

## When to use vs. alternatives

By now you've seen greedy "fail" in two different senses, and conflating them is what trips people up.

For bin packing, greedy heuristics often can't hit the true optimum — but FFD gets close, has a known approximation bound, and that's usually what the interviewer wants. You state the tradeoff and move on. Call that the "greedy is approximate" case.

The cases below are different. Greedy returns an answer that's *incorrect*, not merely suboptimal, and no amount of "better heuristic" fixes it. These are the problems where you need DP, [backtracking](/learn/ai-coding/patterns/backtracking), or something else entirely, and where an AI-generated greedy solution will look plausible until a hidden test case breaks it. Call that the "greedy is wrong" case.

The mechanism is the same as the coin-change counterexample: a locally optimal choice at one step constrains later steps so badly that the overall result is wrong. Here are the shapes you'll see most often:

**0/1 knapsack.** This is the cousin of bin packing. It has the same shape (items with sizes, capacity-limited containers, NP-hard), but it's a different question. Bin packing: pack *everything*, minimize bins. Knapsack: pick a *subset*, maximize value in one bag. Subtle, but important!

FFD on bin packing always returns a *valid* packing; it might use more bins than optimal, but nothing is left behind and nothing overflows. Greedy-by-ratio on 0/1 knapsack also returns a valid subset that fits, but the *value* can be far below the true maximum. In interviews, bin packing often accepts "good enough" (state the approximation) whereas knapsack usually means "find the exact max" which makes it a DP problem.

**Shortest path with negative edges.** In the [graph search & pathfinding](/learn/ai-coding/patterns/graph-search) pattern, Dijkstra's is the greedy go-to — always expand the nearest unvisited node. It works when edge weights are non-negative. Throw in a negative edge and it falls apart. You need Bellman-Ford instead.

**Non-standard coin denominations.** This has the same coin-change trap from earlier. US coins happen to work with greedy, arbitrary sets don't.

**Task scheduling with dependencies.** If tasks depend on each other, greedily picking the shortest task next can violate dependency constraints and produce an invalid schedule. You need [topological sorting](/learn/ai-coding/patterns/topological-sort) or DP.

If you're worried about this, adding test cases where the greedy approach might fail is a great way to make sure it's not a disaster. The AI is often really good at creating these.

If the problem forces you to reason about *combinations* of choices (think: exponential) and not just "pick the best next item," then greedy probably isn't exact. Either reach for DP or [backtracking](/learn/ai-coding/patterns/backtracking), or (for NP-hard packing-style problems) reach for a greedy *heuristic* and say so out loud.

## Prompting the AI

The pattern-specific move for greedy is to use the AI as a counterexample generator *before* you trust the solution. The AI is excellent at producing greedy code; it's also excellent at producing the adversarial input that breaks it. Use both halves.

1. **Name the strategy explicitly in the prompt.** "Sort intervals by end time, then greedily pick the earliest-ending interval that doesn't overlap with the last selection" is much better than "solve this interval problem greedily." Specific prompts produce code you can verify; vague ones produce code you have to trust.
2. **Right after the implementation, ask for adversarial tests.** "Generate test cases where this greedy strategy might fail." The AI will produce inputs that probe the greedy choice property. If your code passes them, your confidence goes up. If it fails any, you've found a real bug.
3. **State explicitly whether you want exact or approximate.** For NP-hard problems, prompt with "use a greedy heuristic and tell me the approximation bound if known." That sets expectations for both you and the AI — and shows the interviewer you understand the difference.

In an interview, saying "The AI suggested a greedy approach here. Let me verify that works by thinking about whether we can always commit to the locally optimal choice," then walking through a small example, is excellent. Even if the greedy approach turns out to be correct, the fact that you questioned it and verified it tells the interviewer you think critically about generated code.

## Verifying the AI's code

Greedy code is short and easy to read, so the bug is almost never in the implementation — it's in the *strategy*, which means a flawlessly written greedy solution can still be wrong.

What to check, in order:

1. **What is the greedy choice?** State it out loud. "This sorts by end time and picks the earliest-ending non-overlapping interval." If you can't state it, you can't verify it.
2. **Does the greedy choice property hold for this problem?** Walk through a small example by hand. Are you ever forced into a corner by an early choice? If yes, the algorithm is wrong even when the code is right.
3. **Have you tested an adversarial input?** A coin-change counterexample (coins = [1, 3, 4], target = 6) is the canonical case of "looks fine, isn't." For your problem, what's the equivalent? Ask the AI to generate one if you can't think of it.
4. **For NP-hard problems, is the code claimed as optimal or as a heuristic?** If the AI's comments say "this returns the optimal answer" and the problem is bin packing or knapsack, that's wrong on its face. Fix the framing in code and in your interview narration.

The single most valuable prompt for greedy verification is "give me a small input where this could fail." Even when nothing fails, the act of asking makes the implicit assumption — that greedy works here — explicit and defensible.

## What interviewers expect

A few specific signals interviewers grade on greedy problems:

* **You reason about correctness, not just performance.** Articulate *why* greedy works for this specific problem. The gold standard is a quick exchange argument: "If we had a non-greedy optimal solution, we could swap in the greedy choice without making it worse." No formal proof needed, but you should be able to sketch the reasoning.
* **You don't conflate "approximate" with "wrong."** Bin packing greedy is approximate (and that's usually fine — state the approximation bound and move on). Coin change with non-standard denominations is wrong (and you need DP). The strongest candidates know which they're dealing with.
* **You name the alternative when greedy is wrong.** "I think this needs DP because the greedy choice at step k affects what's available at step k+2" is a great answer. It shows you understand the algorithm design space well enough to pick the right tool.
* **You treat the AI's greedy output as a hypothesis, not an answer.** Walking through a counterexample search out loud is exactly the muscle interviewers are grading for. The candidate who accepts greedy code at face value is the candidate who ships the wrong answer to the hidden test case.

## Putting it together

Greedy problems in AI coding interviews are about judgment. The AI can write the code. It can sort intervals by end time and iterate through them faster than you can type the function signature. The hard part — deciding whether greedy is the right approach in the first place — still falls to you.

That decision, greedy vs. DP vs. something else entirely, is yours to make. And how you make it, how you reason about it out loud, how you verify the AI's output against edge cases, etc. is what the interview is really measuring.

The strongest candidates treat greedy as a tool they reach for deliberately, knowing why it fits. They can articulate why it works, catch when it doesn't, and pivot to the right alternative without losing momentum.
