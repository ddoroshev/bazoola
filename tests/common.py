from db import *


class TableA(Table):
    name = "a"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text", CHAR(5)),
        ]
    )


class TableB(Table):
    name = "b"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text", CHAR(5)),
            Field("a_id", FK("a")),
        ]
    )


class TableB_NullableFK(Table):
    name = "b2"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text", CHAR(5)),
            Field("a_id", FK("a", null=True)),
        ]
    )


class TableC(Table):
    name = "c"
    schema = Schema(
        [
            Field("id", PK()),
            Field("varchar", CHAR(5)),
            Field("int", INT()),
        ]
    )


class TableD(Table):
    name = "d"
    schema = Schema(
        [
            Field("id", PK()),
            Field("varchar", CHAR(5, null=True)),
            Field("int", INT(null=True)),
        ]
    )
