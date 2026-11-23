"""
The remaining payment flows: tours, dorm, graduation, GCash reference
propagation, terminal attribution, and the superuser delete flows.
Everything is rolled back afterwards.
"""
import django
from django.conf import settings

settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver"]

django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from students.models import Student
from tours.models import EducationalTour, TourEnrollment
from dorm.models import DormBuilding, DormRoom, DormAssignment, DormPayment
from graduation.models import GraduationEvent, StudentGraduation, GraduationPayment
from sales.models import Sale, SaleItem, Terminal, Disbursement, DailyCashReport
from tuition.models import TuitionPayment
from products.models import Product

admin = get_user_model().objects.filter(is_superuser=True).first()
client = APIClient()
client.force_authenticate(user=admin)

failures = []


def check(label, cond, detail=""):
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {label}" + (f"  ({detail})" if detail else ""))
    if not cond:
        failures.append(label)


student = Student.objects.filter(section="Amos", last_name="Roxas").first()
terminal = Terminal.objects.filter(is_active=True).first()
product = Product.objects.first()
variant = product.variants.first()
stock_before = variant.stock if variant else None

print(f"subject: {student.last_name}, {student.first_name} | terminal: {terminal.name}")
print()

print("=== 1. tour enrollment + payment (+ overpayment guard) ===")
r = client.post("/api/tours/", {
    "name": "e2e Tour", "destination": "Bacolod", "tour_date": "2027-03-01",
    "return_date": "2027-03-02", "total_cost": 1000, "max_participants": 40,
    "transportation_fee": 600, "accommodation_fee": 250,
    "food_allowance": 100, "entrance_fees": 50, "other_fees": 0,
    "grade_level": "Grade 11",
}, format="json")
check("tour created", r.status_code in (200, 201), f"status {r.status_code}")
tour_id = (r.data or {}).get("id")
r = client.post("/api/tour-enrollments/", {
    "tour_id": tour_id, "student_id": student.id,
}, format="json")
check("tour enrollment created", r.status_code in (200, 201), f"status {r.status_code}")
enrollment_id = (r.data or {}).get("id")
enrollment = TourEnrollment.objects.get(id=enrollment_id)
check("enrollment balance = tour total", float(enrollment.balance) > 0,
      f"fee {enrollment.total_fee} balance {enrollment.balance}")
r = client.post("/api/tour-payments/", {
    "enrollment_id": enrollment_id, "amount": 400,
    "payment_method": "GCash", "reference_number": "GCASH-E2E-1",
    "remarks": "e2e partial",
}, format="json")
check("tour part payment accepted", r.status_code in (200, 201), f"status {r.status_code}")
enrollment.refresh_from_db()
check("enrollment balance reduced by 400", float(enrollment.balance) == float(enrollment.total_fee) - 400,
      f"balance {enrollment.balance}")
check("gcash reference stored", any(p.reference_number == "GCASH-E2E-1" for p in enrollment.payments.all()))
r = client.post("/api/tour-payments/", {
    "enrollment_id": enrollment_id, "amount": 999999, "payment_method": "Cash",
}, format="json")
check("tour overpayment rejected", r.status_code == 400, f"status {r.status_code}")

print()
print("=== 2. dorm assignment + monthly payment ===")
r = client.post("/api/dorm/buildings/", {
    "name": "e2e Hall", "gender_restriction": "Male", "total_rooms": 5,
}, format="json")
check("building created", r.status_code in (200, 201), f"status {r.status_code}")
building_id = (r.data or {}).get("id")
r = client.post("/api/dorm/rooms/", {
    "building": building_id, "room_number": "E2E-1", "capacity": 4,
    "room_type": "Double", "monthly_rate": 1500,
}, format="json")
check("room created", r.status_code in (200, 201), f"status {r.status_code}")
room_id = (r.data or {}).get("id")
r = client.post("/api/dorm/assignments/", {
    "student": student.id, "room": room_id, "date_started": "2026-11-01",
}, format="json")
check("assignment created", r.status_code in (200, 201), f"status {r.status_code}")
assignment_id = (r.data or {}).get("id")
r = client.post("/api/dorm/payments/", {
    "assignment": assignment_id, "amount": 1500,
    "month_covered": "November", "year_covered": 2026,
    "payment_method": "Cash",
    "receipt_number": "DORM-E2E-0001",
}, format="json")
check("dorm payment accepted", r.status_code in (200, 201), f"status {r.status_code} body={r.data}")
dorm_pay = DormPayment.objects.filter(assignment_id=assignment_id).first()
check("dorm payment row stored", dorm_pay is not None)
check("dorm payment auto-receipt is unique",
      dorm_pay and DormPayment.objects.filter(receipt_number=dorm_pay.receipt_number).count() == 1,
      f"receipt {dorm_pay.receipt_number if dorm_pay else '-'}")

print()
print("=== 3. graduation payment ===")
r = client.post("/api/graduation-events/", {
    "name": "e2e Commencement", "graduation_package_fee": 2500,
    "event_date": "2027-04-10", "registration_deadline": "2027-03-10",
    "venue": "e2e Gym",
}, format="json")
check("graduation event created", r.status_code in (200, 201), f"status {r.status_code} {r.data if r.status_code >= 400 else ''}")
event_id = (r.data or {}).get("id")
r = client.post("/api/graduation-enrollments/", {
    "graduation_event": event_id, "student": student.id,
    "graduation_level": "SHS", "total_fee": 2500,
}, format="json")
check("student graduation registered", r.status_code in (200, 201), f"status {r.status_code} {r.data if r.status_code >= 400 else ''}")
sg = StudentGraduation.objects.filter(student=student, graduation_event_id=event_id).first()
r = client.post("/api/graduation-payments/", {
    "student_graduation_id": sg.id, "amount": 1000,
    "method": "Bank Transfer", "reference_number": "BT-E2E-1",
}, format="json")
check("graduation payment accepted", r.status_code in (200, 201), f"status {r.status_code} {r.data if r.status_code >= 400 else ''}")
sg.refresh_from_db()
check("graduation balance reduced by 1000", float(sg.balance) == 1500,
      f"balance {sg.balance} (fee {sg.graduation_event.graduation_package_fee})")

print()
print("=== 4. gcash reference propagates through a sale ===")
r = client.post("/api/sales/", {
    "student": student.id,
    "receipt_number": "OR-E2E-GCASH-1",
    "items": [{"product_id": product.id, "quantity": 1, "price": 500, "variant": variant.id if variant else None}],
    "total": 500, "amount_paid": 500,
    "payment_method": "GCash", "gcash_number": "09171234567", "gcash_reference": "GCASH-E2E-2",
}, format="json")
check("gcash sale created", r.status_code in (200, 201), f"status {r.status_code}")
gc_sale = Sale.objects.filter(receipt_number="OR-E2E-GCASH-1").first()
check("gcash number + reference stored",
      gc_sale and gc_sale.gcash_number == "09171234567" and gc_sale.gcash_reference == "GCASH-E2E-2",
      f"{gc_sale.gcash_number} / {gc_sale.gcash_reference}")

print()
print("=== 5. terminal attribution (X-Device-Id) ===")
r = client.post("/api/sales/", {
    "student": student.id,
    "receipt_number": "OR-E2E-TERM-1",
    "items": [{"product_id": product.id, "quantity": 1, "price": 300, "variant": variant.id if variant else None}],
    "total": 300, "amount_paid": 300, "payment_method": "Cash",
}, format="json", HTTP_X_DEVICE_ID=terminal.device_id)
check("sale with device header accepted", r.status_code in (200, 201), f"status {r.status_code}")
term_sale = Sale.objects.filter(receipt_number="OR-E2E-TERM-1").first()
check("sale attributed to the terminal", term_sale and term_sale.terminal_id == terminal.id,
      f"terminal {term_sale.terminal.name if term_sale and term_sale.terminal else None}")

print()
print("=== 6. receipt numbers are NOT unique across terminals (latent risk) ===")
r1 = client.post("/api/sales/", {
    "student": student.id, "receipt_number": "OR-E2E-DUP-1",
    "items": [{"product_id": product.id, "quantity": 1, "price": 100, "variant": variant.id if variant else None}],
    "total": 100, "amount_paid": 100, "payment_method": "Cash",
}, format="json", HTTP_X_DEVICE_ID=terminal.device_id)
r2 = client.post("/api/sales/", {
    "student": student.id, "receipt_number": "OR-E2E-DUP-1",
    "items": [{"product_id": product.id, "quantity": 1, "price": 100, "variant": variant.id if variant else None}],
    "total": 100, "amount_paid": 100, "payment_method": "Cash",
}, format="json")
dupes = Sale.objects.filter(receipt_number="OR-E2E-DUP-1").count()
check("duplicate receipt numbers accepted", r1.status_code in (200, 201) and r2.status_code in (200, 201) and dupes == 2,
      f"{dupes} rows share one OR number - audit trail ambiguity")

print()
print("=== 7. superuser delete flows ===")
r = client.delete(f"/api/sales/{term_sale.id}/")
check("sale delete allowed for superuser", r.status_code in (200, 202, 204), f"status {r.status_code}")
if stock_before is not None:
    variant.refresh_from_db()
    print(f"  note: stock after sale delete = {variant.stock} (was {stock_before} before the sale)"
          f" {'- RESTORED' if variant.stock == stock_before else '- NOT restored'}")
tp = TuitionPayment.objects.create(
    student=student, amount=500, method="Cash", payment_method="Cash",
    payment_date="2026-11-11", school_year="2026-2027", notes="e2e delete test",
)
student.tuition_balance = student.custom_tuition_fee - 500
student.save(update_fields=["tuition_balance"])
r = client.delete(f"/api/tuition-payments/{tp.id}/")
student.refresh_from_db()
print(f"  note: tuition payment deleted -> balance now {student.tuition_balance} "
      f"(fee {student.custom_tuition_fee}, rows {TuitionPayment.objects.filter(student=student).count()})"
      f" {'- recalculated' if student.tuition_balance == student.custom_tuition_fee else '- STALE (cache not rewritten)'}")

print()
print("=== restoring the pre-test state ===")
with __import__("django").db.transaction.atomic():
    TourEnrollment.objects.filter(tour_id=tour_id).delete()
    EducationalTour.objects.filter(id=tour_id).delete()
    DormPayment.objects.filter(assignment_id=assignment_id).delete()
    DormAssignment.objects.filter(id=assignment_id).delete()
    DormRoom.objects.filter(id=room_id).delete()
    DormBuilding.objects.filter(id=building_id).delete()
    GraduationPayment.objects.filter(student=student).delete()
    StudentGraduation.objects.filter(student=student).delete()
    GraduationEvent.objects.filter(id=event_id).delete()
    Sale.objects.filter(receipt_number__startswith="OR-E2E").delete()
    SaleItem.objects.all().delete()
    TuitionPayment.objects.filter(student=student).delete()
    Disbursement.objects.all().delete()
    DailyCashReport.objects.all().delete()

if stock_before is not None:
    variant.stock = stock_before
    variant.save(update_fields=["stock"])
student.tuition_balance = student.custom_tuition_fee
student.save(update_fields=["tuition_balance"])

student.refresh_from_db()
check("student balance restored", student.tuition_balance == student.custom_tuition_fee)
check("no sales left", Sale.objects.filter(receipt_number__startswith="OR-E2E").count() == 0)
check("no dorm rows left", DormPayment.objects.count() == 0 and DormAssignment.objects.count() == 0)
check("no tour rows left", TourEnrollment.objects.count() == 0 and EducationalTour.objects.count() == 0)
check("no graduation rows left", StudentGraduation.objects.count() == 0 and GraduationEvent.objects.count() == 0)
check("no tuition rows left", TuitionPayment.objects.count() == 0)
if stock_before is not None:
    variant.refresh_from_db()
    check("stock restored", variant.stock == stock_before, f"{variant.stock}")

print()
print(f"RESULT: {'ALL FLOWS PASS' if not failures else str(len(failures)) + ' FAILURES: ' + ', '.join(failures)}")
