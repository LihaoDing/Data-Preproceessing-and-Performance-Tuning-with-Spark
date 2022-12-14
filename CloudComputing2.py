# -*- coding: utf-8 -*-
"""Assignment2_08_RE_ldin7836_Lihao_Ding_(3) (1).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1HcyKxViL_GFujr1yxlu5G1bLdsNbNBgl


## Installing pyspark

The following cell install the latest pyspark package
"""

#!pip install pyspark

"""## Mounting Google Drive

The following cell mounts your google drive in the virtual machine runing the notebook. You will be asked to authenticate your account to access Google drive. Once authenticated, your google drive is mounted at `/content/drive`. Anything in your google drive can be accessed from `/content/drive/MyDrive`.
"""

#from google.colab import drive
#drive.mount('/content/drive', force_remount=True)

"""## Initializing spark and import all library

"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode
from pyspark.sql.functions import broadcast
from pyspark.sql.functions import udf
from pyspark.sql.functions import explode_outer
from pyspark.sql.functions import round
from pyspark.sql.functions import row_number
from pyspark.sql.window import Window
from pyspark.sql.types import StructType, StructField, StringType,IntegerType, FloatType, ArrayType
spark = SparkSession \
    .builder \
    .appName("COMP5349 Assignment2") \
    .getOrCreate()


# reference: https://colab.research.google.com/drive/1cdTy7-sLgO8FFliMMlUGn6LiVmVZOTT-?usp=sharing

"""## READ DATA
Read from json file(test.json) to dataframe.
"""

# Read data and explode "data"
test_data_df = spark.read.json("s3://comp5349-2022/test.json")
test_data_df = test_data_df.select(explode("data").alias("data"))
test_data_df.count()

# Explode "paragraph" & "qas", keep necessary column
test_data_df = test_data_df.select(explode("data.paragraphs").alias("paragraphs"), col("data.title"))
test_data_df = test_data_df.select(explode("paragraphs.qas").alias("qas"), col("paragraphs.context").alias("context"), col("title"))
test_data_df.printSchema()

# This function is used to cut of context into sequence
# Each sequence in a contract is saved by an array of the following defined return type schema
@udf(returnType = ArrayType(StructType([
    StructField("start", IntegerType(), False),
    StructField("end", IntegerType(), False),
    StructField("context", StringType(), False)
])))
def cut_udf(context):
  return_list = []
  current_string = context
  start = 0
  end = 4096
  while start < len(current_string):
    if end >= len(current_string):
      return_list.append((start, len(current_string), current_string[start:len(current_string)]))
      start += 2048
      end += 2048
    else:
      return_list.append((start, end, current_string[start:end]))
      start += 2048
      end += 2048 
  return return_list

# use the previous function to segment contect into different sequence saved in schema of Array(in column "cut")
cut_test_df = test_data_df.select(cut_udf(col("context")).alias("cut"), col("qas"), col("title"))
cut_test_df.printSchema()

cut_test_df.show(5)

# Explode "cut" column to save attribute in the explode column(cut and qas) as column
cut_test_df = cut_test_df.select(explode("cut").alias("context"), col("qas"), col("title"))
cut_test_df = cut_test_df.select(col("context.start").alias("start"), col("context.end").alias("end"), col("context.context").alias("sequence"), col("qas.id"), col("qas.question"), col("qas.is_impossible"), col("qas.answers"), col("title"))

cut_test_df.show(4)

# Use explode_answers to explode "answers" while keep empty answer
cut_test_df = cut_test_df.select(explode_outer("answers").alias("answer"), col("answer.answer_start"), col("answer.text"), col("id"), col("question"), col("is_impossible"), col("start"), col("end"), col("sequence"), col("title")).drop("answer")

cut_test_df.show(4)

cut_test_df.printSchema()

# This function is used to find the start and end position of an answer text in the segmented sequence
# Result is saved in a defined schema: sestart -> sequence start; seend -> sequence end; setext -> answer text; neg_pos -> is this sample positive or possible negative or impossible negative
@udf(returnType = StructType([
    StructField("sestart", IntegerType(), False),
    StructField("seend", IntegerType(), False),
    StructField("setext", StringType(), True),
    StructField("neg_pos", StringType(), True)
]))
def calculate_udf(answer_start, text, start, end, is_impossible):
  if is_impossible:
    return (0, 0, text, "impossible_negative")
  if text == None:
    return (0, 0, text, "possible_negative")
  answer_end = answer_start + len(text)
  if answer_end <= start or answer_start >= end:
    return (0, 0, text, "possible_negative")
  elif answer_end >= start and answer_end < end and answer_start <= start:
    return (0, answer_end - start, text, "positive")
  elif answer_start >= start and answer_end <= end:
    return (answer_start - start, answer_end - start, text, "positive")
  elif answer_start < start and answer_end > end:
    return (0, end - start, text, "positive")
  elif answer_start > start and answer_start <= end and answer_end > end:
    return (answer_start - start, end - start, text, "positive")

# Use the defined function above to calculate the start position, end position, and imposs_neg/poss_neg/possitive
# Then keep all the necessary column in one layer
# The "all_sample_df" is the result of step 1 of this assignment. It saves all data of all samples.
calculate_position_df = cut_test_df.select(calculate_udf(col("answer_start"), col("text"), col("start"), col("end"), col("is_impossible")).alias("sample"), col("id"), col("question"), col("is_impossible"), col("sequence"), col("title"))
all_sample_df = calculate_position_df.select(col("sample.sestart").alias("answer_start"), col("sample.seend").alias("answer_end"), col("sample.setext").alias("answer_text"), col("sample.neg_pos").alias("answer_neg_pos"), col("id"), col("question"), col("is_impossible"), col("sequence"), col("title"))
all_sample_df.printSchema()

all_sample_df.show(4)

all_sample_df.count()

"""## Step2.1 make impossible negative equals avergae(positive) of that question"""

# Find positive sequence, unique imoissible_negative sequence, unique possible_negative sequence
positive_df = all_sample_df.filter(all_sample_df.answer_neg_pos == "positive")
imoissible_negative_df = all_sample_df.filter(all_sample_df.answer_neg_pos == "impossible_negative").join(positive_df, ["sequence"], "leftanti")

# Find positive sample number of each question and question numbers the devide them get the average value
average_pos = positive_df.groupby("question").count().withColumnRenamed("count", "num_pos").join(positive_df.groupby("question", "title").count().groupBy("question").count(), "question").select(col("question"), round(col("num_pos") / col("count"), 0).alias("average"))
#average_pos.show(4)

# use left join to give the corresponding average number of positive sample of question to every selected impossible negative sample
imoissible_negative_df = imoissible_negative_df.join(average_pos, ["question"], "left")
imoissible_negative_df.count()

imoissible_negative_df.show(4)

"""Delete negative sequence sample number large than average"""

# This Window is used to number samples with same question
# Then sample with number larger than average number of positive sample of that question will be dropped

spec = Window.partitionBy("question").orderBy("question")
raw_imnegative_result = imoissible_negative_df.withColumn("num", row_number().over(spec)).filter(col("num") <= col("average"))

# "window to add index number" reference: https://blog.csdn.net/weixin_43668299/article/details/103269810?spm=1001.2101.3001.6650.1&utm_medium=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7Edefault-1-103269810-blog-89191332.pc_relevant_default&depth_1-utm_source=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7Edefault-1-103269810-blog-89191332.pc_relevant_default&utm_relevant_index=2
# "filter two column compare" reference: https://stackoverflow.com/questions/66793720/pyspark-filtering-rows-on-multiple-columns

raw_imnegative_result.show(5)

raw_imnegative_result.count()

"""## Step2.2 make possible negative equals positive sample number of that question"""

# Find all possible negative sequence and the leftanti join with "positive sequence", "result impossible negative sequence" to remove the duplicated sequence in possible negative sequence
reduced_possible_negative_df = all_sample_df.filter(all_sample_df.answer_neg_pos == "possible_negative").join(positive_df, ["sequence"], "leftanti").join(raw_imnegative_result, ["sequence"], "leftanti")

# Find the number of positive sample of each question and join the number with reduced_possible_negative by "id"
combine_posneg = reduced_possible_negative_df.join(positive_df.groupby("id").count(), ["id"], "left")

# This Window is used to number samples with same id
# Then sample with number larger than sum number of positive sample of that question will be dropped
spec2 = Window.partitionBy("id").orderBy("id")
raw_posnegative_result = combine_posneg.withColumn("num", row_number().over(spec2)).filter(col("num") <= col("count"))
raw_posnegative_result.count()

# "window to add index number" reference: https://blog.csdn.net/weixin_43668299/article/details/103269810?spm=1001.2101.3001.6650.1&utm_medium=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7Edefault-1-103269810-blog-89191332.pc_relevant_default&depth_1-utm_source=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7Edefault-1-103269810-blog-89191332.pc_relevant_default&utm_relevant_index=2
# "filter two column compare" reference: https://stackoverflow.com/questions/66793720/pyspark-filtering-rows-on-multiple-columns

raw_posnegative_result.show(5)

"""### Rewrite data of positive, possible_negative, and impossible_negative to sample schema"""

final_possible_negative_df = raw_posnegative_result.select(col("sequence").alias("source"), col("question"), col("answer_start"), col("answer_end"))
final_possible_negative_df.printSchema()

final_impossible_negative_df = raw_imnegative_result.select(col("sequence").alias("source"), col("question"), col("answer_start"), col("answer_end"))
final_impossible_negative_df.printSchema()

final_positive_df = positive_df.select(col("sequence").alias("source"), col("question"), col("answer_start"), col("answer_end"))
final_positive_df.printSchema()

"""### Union positive, possible negative, and impossible negative together to get the final result"""

final_result = final_possible_negative_df.union(final_impossible_negative_df).union(final_positive_df)

final_result.count()

final_result.show(10)

"""## Write the final result to file."""

out = ",\n".join(final_result.coalesce(1).toJSON().collect())
f = open("assignment2_result.json", "w")
f.write("[ " + out + " ]")

spark.stop()