-- AlterTable
ALTER TABLE "Order" ADD COLUMN     "shippingCost" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "shippingMethod" TEXT;
