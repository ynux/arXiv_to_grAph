## A Spark Experiment

Exercise for the Spark: The Definitive Guide. Chapter 26: Classification

```
head -100 db.json > db100.json
while read line; do jq -c '{ pub_year: .published_parsed[0], arxiv_primary_category: .arxiv_primary_category.term, version: ._version, author }' >> classify.json; done < db100.json
```
I only chose simple features and excluded arrays such as the authors and tag terms. Note that the "author" isn't really the authors, but the user who uploaded the paper, usually one of the real authors. The authors, however, are an array of names, which would complicate things. This example is meant to be as simple as doable, even if this means sacrificing content.

We are left with the year of publishing, the primary category and the uploading author to explain if there was an update of the paper (version > 1) or not. 

### When do authors update their Paper?

From a non representative survey, authors upload their paper when it is done in their eyes and ready to be submitted for publications. Other researchers will be notified and can give some first feedback, e.g. that a reference to a very similar result it missing. If the author agrees that this is important, she will do an update on arXiv. Publications in journals take several months to years. The reviews typically lead to substantial changes. Once this is completed, there may be another update on arXiv. In the unlikely event that an error is found another update may occur.

Start a local spark cluster, start a pyspark session, and run:
```

path = "../gitprojects/arXiv_to_grAph/spark/classify.json"

arxson = spark.read.json(path)
arxson.show()
arxson.printSchema()
```
Consider removing null values with something like `arxson = arxson.filter(arxson.arxiv_primary_category).isNotNull()`

Get it into the proper form for Estimation - back to chapter 25. We want a binary label: Version = 1, or higher. The Binarizer expects a double. Also, we need a feature vector. 
```
from pyspark.ml.feature import Binarizer
arxson = arxson.withColumn("version", arxson.version.cast("double"))
versionbinarizer = Binarizer(threshold=1.5, inputCol="version", outputCol="version_gt_one")
binarized_arxson = versionbinarizer.transform(arxson)
from pyspark.ml.feature import RFormula
arxformula = RFormula(formula="version_gt_one ~ arxiv_primary_category + author + pub_year", featuresCol="features", labelCol="label")
arxclass = arxformula.fit(binarized_arxson).transform(binarized_arxson)
arxclass.select("features","label").show()
```
Now this should have been 80% of the work, according to data science conventional wisdom.
```
from pyspark.ml.classification import LogisticRegression
lr = LogisticRegression()
bInput = arxclass.select("features","label")
lrModel = lr.fit(bInput)

print lrModel.coefficients
print lrModel.intercept
```
I ignored some warnings 
```
19/08/23 10:08:05 WARN BLAS: Failed to load implementation from: com.github.fommil.netlib.NativeSystemBLAS
19/08/23 10:08:05 WARN BLAS: Failed to load implementation from: com.github.fommil.netlib.NativeRefBLAS
```
The result is too good to be true, the area under ROC being close to one. It's all on the training set, and badly overfitted with the author variable. We have a subset of 100 papers, and 77 unique authors (`cat db100.json | jq -c '{ author }' | sort -u | wc -l`). With the next new paper, there will be a new author, and our model will be lost. 
```
summary = lrModel.summary
print summary.areaUnderROC
summary.roc.show()
summary.pr.show()
```
```
>>> print summary.areaUnderROC
0.991704805492
```
Let's repeat the exercise without the author. This leaves us with the publication year and primary category to guess if the paper was updated.
For some reason, I run into an error now.
```
ERROR LBFGS: Failure! Resetting history: breeze.optimize.FirstOrderException: Line search failed
```
This is bad, I'm in spark spark-2.4.3-bin-hadoop2.7, Python 2.7.10. It looks like a spark issue, still I'll try in scala. This time, we ensure that version is a double from the start.

```
val path = "../gitprojects/arXiv_to_grAph/spark/classify.json"
val arxson = spark.read.json(path).selectExpr("arxiv_primary_category", "author", "pub_year", "cast(version as double) as version")
arxson.show()
arxson.printSchema()
import org.apache.spark.ml.feature.Binarizer
val versionbinarizer: Binarizer = new Binarizer().setInputCol("version").setOutputCol("version_gt_one").setThreshold(1.5)
val binarized_arxson = versionbinarizer.transform(arxson)
import org.apache.spark.ml.feature.RFormula
val arxformula: RFormula = new RFormula().setFormula("version_gt_one ~ arxiv_primary_category + pub_year").setFeaturesCol("features").setLabelCol("label")
val arxclass = arxformula.fit(binarized_arxson).transform(binarized_arxson)
arxclass.select("features","label").show()
import org.apache.spark.ml.classification.LogisticRegression
val lr = new LogisticRegression()
val bInput = arxclass.select("features","label")
val lrModel = lr.fit(bInput)

println(lrModel.coefficients)
println(lrModel.intercept)
```
As expected, it throws the same errors. Something must have worked, though, because it also comes back with 
```
println(bSummary.areaUnderROC)
0.6953661327231122
```
What does this mean? If the years where very close to now (2019), we'd expect recent papers to have fewer updates. However, the published_years range from 1992 to 1999. The areaUnderROC is above 0.5 which gives hope. Then again, if I always guessed "0" (or always "1"), would that do the trick, too?  
```
scala> arxclass.filter("label == 1.0").count()
res12: Long = 23

scala> arxclass.filter("label == 0.0").count()
res13: Long = 76

scala> 
```
So I'll do *better* always guessing 0.0. And use less resources, too. Again, we experience the limits of usefulness of machine learning.

Let's ignore all issues and create a pipeline for the first model. Assume that the data is loaded with "result" as double. Back in python, following a datacamp intro example:
```
from pyspark.ml.feature import Binarizer, RFormula
from pyspark.ml.classification import LogisticRegression
from pyspark.ml import Pipeline
import pyspark.ml.evaluation as evals
import pyspark.ml.tuning as tune
import numpy as np

path = "../gitprojects/arXiv_to_grAph/spark/classify.json"
arxson = spark.read.json(path).selectExpr("arxiv_primary_category", "author", "pub_year", "cast(version as double) as version")

versionbinarizer = Binarizer(threshold=1.5, inputCol="version", outputCol="version_gt_one")
arxformula = RFormula(formula="version_gt_one ~ arxiv_primary_category + author + pub_year", featuresCol="features", labelCol="label")
 
arxiv_pipeline = Pipeline(stages=[versionbinarizer, arxformula]) 
piped_arxiv = arxiv_pipeline.fit(arxson).transform(arxson)
training, test = piped_arxiv.randomSplit([.6,.4])

lr = LogisticRegression()
evaluator = evals.BinaryClassificationEvaluator(metricName="areaUnderROC")

grid = tune.ParamGridBuilder()
grid = grid.addGrid(lr.regParam, np.arange(0, .1, .01))
grid = grid.addGrid(lr.elasticNetParam,[0,1] )
grid = grid.build()

cv = tune.CrossValidator(estimator=lr, estimatorParamMaps=grid, evaluator=evaluator)

best_lr = lr.fit(training)
test_results = best_lr.transform(test)

```

0.510344827586 ...  well. We knew this, but it still hurts to see it. With the authorless model:
```
arxformula = RFormula(formula="version_gt_one ~ arxiv_primary_category + pub_year", featuresCol="features", labelCol="label")
...
>>> print(evaluator.evaluate(test_results))                                     0.589655172414
>>> 

```
Ouch. Does increasing the data volume help, from 100 to 6656, the full data set?
It runs fast, the author-model goes up to 0.596508584978, the authorless one down to 0.523086887446 . 


How would i define my always-0-model?
What if I restricted to authors with more than 10 papers?
```
cat ../db.json | jq -c '{ author }' | sort | uniq -c | sort -n | sed '/^   /d' | cut -d\" -f4 > more_than_10.csv
```
If you get the impression that i did DevOps for too long to prefer SQL over sed, I won't blame you. Now, however, I have to join the authors with our dataframe.

```
path_csv="../gitprojects/arXiv_to_grAph/spark/more_than_10.csv"
from pyspark.sql import SQLContext
from pyspark.sql.types import StructType, StructField, StringType

author_schema = StructType([ StructField("author", StringType(), True)])
more_than_10 = spark.read.csv(path_csv, header="false", schema=author_schema)

arxson_morethan10 = more_than_10.join(arxson, "author")
arxson_morethan10.count()
```
We end up with 1994 rows, this looks promising. With author, our score goes up to 0.643755166253 ! Isn't it amazing. Now we expect the authorless model to be worse - unless, of course, the same authors publish with the same primary category (possible) or always in the same year (less so). And it meets our expectations: 0.490128898684 . All time low.

But the other one is actually better than our dumb estimator!
```
>>> arxson_morethan10.filter("version > 1.0").count()
1178
>>> arxson_morethan10.filter("version == 1.0").count()
816
>>> arxson_morethan10.count()
1994
>>> 1178.0/1994
0.5907723169508525
>>> 
```
I think this is a good point for claiming victory and leaving the field.
