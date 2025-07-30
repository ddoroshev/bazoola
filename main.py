from __future__ import annotations

from tqdm import tqdm

from bazoola import *


class TableBooks(Table):
    name = "books"
    schema = Schema(
        [
            Field("id", PK()),
            Field("title", CHAR(20)),
            Field("author_id", FK("authors")),
            Field("year", INT(null=True)),
        ]
    )


class TableAuthors(Table):
    name = "authors"
    schema = Schema(
        [
            Field("id", PK()),
            Field("name", CHAR(20)),
        ]
    )


def run() -> None:
    db = DB([TableBooks, TableAuthors])

    for i in tqdm(range(1000)):
        db.insert("authors", {"name": f"Author #{i + 1}"})

    for i in tqdm(range(1000)):
        book_id = i + 1
        db.insert(
            "books",
            {
                "title": f"Book #{book_id}",
                "author_id": book_id,
                "year": 1990,
            },
        )

    book_1 = db.find_by_id("books", 1000, joins=[Join("author_id", "author", "authors")])
    if not book_1:
        print("Can't find book by ID=100")
        return
    book_2 = db.find_by_id("books", 333, joins=[Join("author_id", "author", "authors")])
    if not book_2:
        print("Can't find book by ID=555")
        return

    print("Selected books:")
    print(book_1)
    print(book_2)
    print("Found by title")
    books_found = db.find_by_cond(
        "books", SUBSTR(title="ook #39"), joins=[Join("author_id", "author", "authors")]
    )
    for book in books_found:
        print(book)

    for i in tqdm(range(500)):
        book_id = (i + 1) * 2
        db.delete_by_id("books", book_id)

    for i in tqdm(range(500)):
        db.insert(
            "books",
            {
                "title": f"NEW Book #{book_id}",
                "author_id": book_id,
                "year": 1991,
            },
        )

    db.close()


if __name__ == "__main__":
    run()
