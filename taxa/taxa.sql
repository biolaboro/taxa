PRAGMA foreign_keys = OFF;

-- Schema: tax
ATTACH "tax.sdb" AS "tax";
BEGIN;
CREATE TABLE "tax"."tax_merged"(
  "old_tax_id" INTEGER PRIMARY KEY NOT NULL,
  "new_tax_id" INTEGER NOT NULL
);
CREATE TABLE "tax"."tax_node"(
  "tax_id" INTEGER PRIMARY KEY NOT NULL,
  "parent_tax_id" INTEGER NOT NULL,
  "rank" TEXT NOT NULL
);
CREATE TABLE "tax"."tax_name"(
  "id" INTEGER PRIMARY KEY NOT NULL,
  "tax_id" INTEGER NOT NULL,
  "name_txt" TEXT NOT NULL,
  "unique_name" TEXT,
  "name_class" TEXT NOT NULL
);
CREATE INDEX "tax"."tax_name.index" ON "tax_name" ("tax_id");
COMMIT;
