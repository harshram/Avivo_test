import argparse
from F1_QA import prepare_embeddings, answer_question


def run():
    parser = argparse.ArgumentParser(description="F1 QA assistant CLI")
    parser.add_argument("--csv", default="FormulaOne_Data.Csv", help="Path to the CSV file (default: FormulaOne_Data.Csv)")
    parser.add_argument("--max-docs", type=int, default=10, help="Max documents to use as context")
    args = parser.parse_args()

    embeddings, sections = prepare_embeddings(args.csv)
    print("Embeddings prepared. Ask questions (empty line to quit).")

    try:
        while True:
            q = input("Question: ")
            if not q or not q.strip():
                break
            ans = answer_question(q, embeddings, args.max_docs)
            print("\n" + ans + "\n")
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    run()
