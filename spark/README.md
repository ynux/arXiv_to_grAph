## A Spark Experiment

Exercise for the Spark: The Definitive Guide. Chapter 26: Classification

```
head -100 db.json > db100.json
while read line; do jq '{ pub_year: .published_parsed[0], arxiv_primary_category: .arxiv_primary_category.term, version: ._version, author }' >> classify.json; done < db100.json
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
