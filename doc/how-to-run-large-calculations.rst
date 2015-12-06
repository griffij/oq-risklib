How to run large calculations: tools and tips
==============================================


1. *Stay updated*. This is the most important performance tip.  We
work continuosly on improving the performance of the OpenQuake
calculators and staying is the most important thing to have the best
performance, both in terms of computing time and memory
occupation. Ask on the mailing list: we will tell you if the
calculation you are using has been improved significantly recently and
if it is a good idea to migrate to the latest nightly builds. Usually
the nightly builds are *very reliable*: after all, they are produced
by our Continuous Integration system only if they pass a substantial
test suite. So don't be scared of using the nightly builds.

2. *Run a protopype first*. The second most important tip is that
before running a large computation you should have an idea of its
bottlenecks and problems. The only way to know this is to run a
prototype, i.e. a smaller version of the full computation first.
`oq-lite` offers a number of way to reduce a large computation to
a smaller prototype: please take advantage of such features.
Basically you want to reduce the number of sites/assets, the number
of sources in the source model, the size of the logic tree, the
number of ruptures, etc.

3. *Build a precalculation report*. `oq-lite` can tell you how big a
computation is without running it.

4. *In the case of large logic trees, set individual_curves=False*.
More often than not, in the case of large logic trees one is interested
in computing the mean curves and the quantile curves, not the individual
curves. If this is the case, set the parameter `individual_curves` to `False`
and you will save the time and space needed to save the individual curves.

5. *For event based calculations, set ses_per_logic_tree_path=1*.
The number of ruptures generated is determined by the product
`ses_per_logic_tree_path * investigation_time` (the time span). However, it is
much faster to have `ses_per_logic_tree_path` small and `investigation_time`
rather than the opposite. In the industry it is customary to use a
time span of 10,000 years; *never* set `investigation_time=1` and
`ses_per_logic_tree_path=10000`, instead set `investigation_time=10000` and
`ses_per_logic_tree_path=1`.
