-- AlterTable
ALTER TABLE "Order" ADD COLUMN     "trackingNumber" TEXT;

-- CreateTable
CREATE TABLE "OrderEvent" (
    "id" TEXT NOT NULL,
    "orderId" TEXT NOT NULL,
    "status" "OrderStatus" NOT NULL,
    "note" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "OrderEvent_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "OrderEvent" ADD CONSTRAINT "OrderEvent_orderId_fkey" FOREIGN KEY ("orderId") REFERENCES "Order"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- Backfill: one PENDING event per existing order
INSERT INTO "OrderEvent" ("id", "orderId", "status", "createdAt")
SELECT 'evt_' || gen_random_uuid(), "id", 'PENDING', "createdAt"
FROM "Order" o
WHERE NOT EXISTS (SELECT 1 FROM "OrderEvent" e WHERE e."orderId" = o."id");
