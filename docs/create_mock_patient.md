# Synthetic Patient Generator

This script creates the mock patient PDF used by the RAG demo.

## Purpose

- Generate synthetic clinical source material.
- Avoid dependency on real patient data.
- Provide a stable PDF for ChromaDB ingestion and patient briefing demos.

## Current use

The generated file is stored in `data/sample_patients/PT-2024-001-Rajesh-Kumar.pdf` and is used by the patient history briefing flow.

## Why it remains useful

It gives the repository a simple, repeatable source document for the RAG pipeline and demo walkthrough.
