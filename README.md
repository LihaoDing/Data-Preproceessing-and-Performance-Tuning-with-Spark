# Contract Analysis System
## Overview

This project develops a scalable system for pre-processing and analyzing contractual documents using Apache Spark. It involves handling complex data structures, optimizing performance, and leveraging the cloud's parallel processing capabilities. The system processes contractual documents by segmenting them into smaller, manageable sequences, enabling efficient question-answering tasks over these contracts. This is particularly useful in scenarios requiring the extraction of specific information from large volumes of legal documents.

## System Architecture

The system utilizes Apache Spark to process data stored in JSON format, comprising over 13,000 clauses from 510 contracts categorized into 41 question-answer pairs. It uses Spark's RDD and SQL API to manage data flow, perform transformations, and execute jobs in a cluster environment. The architecture is designed to support scalability and efficient resource management, adapting to different cluster sizes and configurations.

## Features

Data Preprocessing: Converts raw JSON data into a structured format suitable for model training. This includes segmenting contracts into overlapping sequences using a sliding window approach.
Sample Generation: Produces training samples by identifying relevant text segments that answer specific questions posed within the contractual text.
Performance Optimization: Implements tuning strategies to optimize memory consumption and processing speed across multiple nodes.
Scalability: Evaluates the system's performance with varying data sizes and cluster configurations to ensure efficient processing regardless of the workload.

## Installation
Ensure you have Apache Spark installed and configured on your system or cloud environment.
Clone the repository and navigate to the project directory:
```
git clone https://github.com/LihaoDing/Data-Preproceessing-and-Performance-Tuning-with-Spark.git
cd Data-Preproceessing-and-Performance-Tuning-with-Spark
```

## Usage
To run the system, use the provided script submit_client.sh with the following command:

```
./submit_client.sh output_directory
```
This script configures and submits the Spark job to your cluster.

## Output
The processed data is output in JSON format, containing fields for source, question, answer start, and answer end. Each entry corresponds to a potential answer segment within the contract.

## Contributing
Contributions to the project are welcome. Please fork the repository and submit pull requests with your proposed changes.

License
This project is licensed under the MIT License - see the LICENSE.md file for details.