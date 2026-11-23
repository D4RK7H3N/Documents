from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .base import auth, login, make_assignment, make_section, make_student, make_subject, make_user


class GradingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_user("admin", "adminpass123", "admin")
        self.teacher = make_user("teacher1", "teacherpass123", "teacher")
        self.other_teacher = make_user("teacher2", "teacherpass123", "teacher")
        self.section = make_section()
        self.subject = make_subject("General Physics 1", "core")
        self.assignment = make_assignment(self.subject, self.section, self.teacher)
        self.student, self.student_pw = make_student("123456789012", "Sample Student", self.section, self.admin)
        self.student2, self.student2_pw = make_student("123456789099", "Second Student", self.section, self.admin)
        res = login(self.client, "teacher1", "teacherpass123")
        auth(self.client, res.data["access"])
        self.teacher_token = res.data["access"]

    def create_assessment(self, component, quarter, hps, title=None):
        return self.client.post(
            f"/api/v1/classes/{self.assignment.id}/assessments/",
            {
                "class_assignment": self.assignment.id,
                "component": component,
                "quarter": quarter,
                "title": title or f"{component} exam",
                "highest_possible_score": hps,
            },
            format="json",
        )

    def save_scores(self, assessment_id, payload):
        return self.client.put(
            f"/api/v1/assessments/{assessment_id}/scores/", {"scores": payload}, format="json"
        )

    def login_student(self, profile, password):
        client = APIClient()
        res = login(client, profile.lrn, password)
        self.assertEqual(res.status_code, 200)
        auth(client, res.data["access"])
        return client

    def test_full_recomputation_cycle_matches_manual_record(self):
        ww = self.create_assessment("WW", 1, 100)
        pt = self.create_assessment("PT", 1, 100)
        qa = self.create_assessment("QA", 1, 50)
        self.assertEqual(ww.status_code, 201)
        self.assertEqual(
            self.save_scores(ww.data["id"], [{"student_id": self.student.id, "raw": 78}]).status_code, 200
        )
        self.save_scores(pt.data["id"], [{"student_id": self.student.id, "raw": 85}])
        self.save_scores(qa.data["id"], [{"student_id": self.student.id, "raw": 42}])

        student_client = self.login_student(self.student, self.student_pw)
        grades = student_client.get("/api/v1/me/grades/?semester=1").data
        subject = grades["subjects"][0]
        self.assertEqual(subject["q1"], 89)
        self.assertIsNone(subject["final"])
        self.assertIsNone(grades["general_average"])
        self.assertIsNotNone(grades["last_updated"])

        self.create_assessment("WW", 2, 100, "WW q2")
        self.create_assessment("PT", 2, 100, "PT q2")
        qa2 = self.create_assessment("QA", 2, 50, "QA q2")
        ww2 = self.client.get(f"/api/v1/classes/{self.assignment.id}/assessments/?quarter=2").data
        by_component = {a["component"]: a["id"] for a in ww2}
        self.save_scores(by_component["WW"], [{"student_id": self.student.id, "raw": 84}])
        self.save_scores(by_component["PT"], [{"student_id": self.student.id, "raw": 86}])
        self.save_scores(by_component["QA"], [{"student_id": self.student.id, "raw": 44}])

        grades = student_client.get("/api/v1/me/grades/?semester=1").data
        subject = grades["subjects"][0]
        self.assertEqual(subject["q1"], 89)
        self.assertEqual(subject["q2"], 91)
        self.assertEqual(subject["final"], 90)
        self.assertEqual(grades["general_average"], 90)

    def test_blank_and_zero_semantics(self):
        ww = self.create_assessment("WW", 1, 100)
        pt = self.create_assessment("PT", 1, 100)
        qa = self.create_assessment("QA", 1, 50)
        self.save_scores(ww.data["id"], [{"student_id": self.student2.id, "raw": None}])
        self.save_scores(pt.data["id"], [{"student_id": self.student2.id, "raw": 0}])
        self.save_scores(qa.data["id"], [{"student_id": self.student2.id, "raw": None}])
        student_client = self.login_student(self.student2, self.student2_pw)
        grades = student_client.get("/api/v1/me/grades/?semester=1").data
        self.assertEqual(grades["subjects"][0]["q1"], 60)

        class_grades = self.client.get(f"/api/v1/classes/{self.assignment.id}/grades/?quarter=1").data
        row = next(r for r in class_grades["students"] if r["student_id"] == self.student2.id)
        self.assertEqual(row["blanks"], 2)
        self.assertEqual(row["grade"], 60)

    def test_score_above_hps_rejected(self):
        qa = self.create_assessment("QA", 1, 50)
        res = self.save_scores(qa.data["id"], [{"student_id": self.student.id, "raw": 51}])
        self.assertEqual(res.status_code, 400)

    def test_negative_score_rejected(self):
        qa = self.create_assessment("QA", 1, 50)
        res = self.save_scores(qa.data["id"], [{"student_id": self.student.id, "raw": -1}])
        self.assertEqual(res.status_code, 400)

    def test_unassigned_teacher_forbidden(self):
        res = login(APIClient(), "teacher2", "teacherpass123")
        client = APIClient()
        auth(client, res.data["access"])
        self.assertEqual(client.get(f"/api/v1/classes/{self.assignment.id}/assessments/").status_code, 403)
        self.assertEqual(
            client.get(f"/api/v1/classes/{self.assignment.id}/grades/").status_code, 403
        )

    def test_teacher_classes_lists_only_own(self):
        classes = self.client.get("/api/v1/teacher/classes/")
        self.assertEqual(classes.status_code, 200)
        results = classes.data["results"] if "results" in classes.data else classes.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["teacher_name"], "teacher1")

    def test_quarter_lock_blocks_teacher_and_audits(self):
        qa = self.create_assessment("QA", 1, 50)
        admin_client = APIClient()
        res = login(admin_client, "admin", "adminpass123")
        auth(admin_client, res.data["access"])
        lock = admin_client.post(f"/api/v1/admin/classes/{self.assignment.id}/quarters/1/lock/")
        self.assertEqual(lock.status_code, 200)

        blocked = self.save_scores(qa.data["id"], [{"student_id": self.student.id, "raw": 10}])
        self.assertEqual(blocked.status_code, 409)
        blocked_create = self.create_assessment("WW", 1, 100, "late WW")
        self.assertEqual(blocked_create.status_code, 409)

        audit = admin_client.get("/api/v1/admin/audit-log/?action=quarter.lock")
        entries = audit.data["results"]
        self.assertTrue(any(e["action"] == "quarter.lock" for e in entries))

        unlock = admin_client.delete(f"/api/v1/admin/classes/{self.assignment.id}/quarters/1/lock/")
        self.assertEqual(unlock.status_code, 200)
        ok = self.save_scores(qa.data["id"], [{"student_id": self.student.id, "raw": 10}])
        self.assertEqual(ok.status_code, 200)

    def test_csv_import_and_student_login(self):
        csv_content = "lrn,name,section\n123456789001,Imported One,Lovelace\n123456789002,Imported Two,Lovelace\n"
        admin_client = APIClient()
        res = login(admin_client, "admin", "adminpass123")
        auth(admin_client, res.data["access"])
        upload = admin_client.post(
            "/api/v1/admin/students/import/",
            {"file": SimpleUploadedFile("students.csv", csv_content.encode(), content_type="text/csv")},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201)
        self.assertEqual(len(upload.data["imported"]), 2)
        temp_password = upload.data["imported"][0]["temporary_password"]
        res = login(self.client, "123456789001", temp_password)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["must_change_password"])

    def test_admin_reset_password_flow(self):
        admin_client = APIClient()
        res = login(admin_client, "admin", "adminpass123")
        auth(admin_client, res.data["access"])
        reset = admin_client.post(f"/api/v1/admin/users/{self.teacher.id}/reset-password/")
        self.assertEqual(reset.status_code, 200)
        temp = reset.data["temporary_password"]
        res = login(APIClient(), "teacher1", temp)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["must_change_password"])

    def test_grading_config_update_recomputes_and_audits(self):
        ww = self.create_assessment("WW", 1, 100)
        pt = self.create_assessment("PT", 1, 100)
        qa = self.create_assessment("QA", 1, 50)
        self.save_scores(ww.data["id"], [{"student_id": self.student.id, "raw": 78}])
        self.save_scores(pt.data["id"], [{"student_id": self.student.id, "raw": 85}])
        self.save_scores(qa.data["id"], [{"student_id": self.student.id, "raw": 42}])
        student_client = self.login_student(self.student, self.student_pw)
        self.assertEqual(student_client.get("/api/v1/me/grades/?semester=1").data["subjects"][0]["q1"], 89)

        admin_client = APIClient()
        res = login(admin_client, "admin", "adminpass123")
        auth(admin_client, res.data["access"])
        config = admin_client.get("/api/v1/admin/grading-config/").data
        config["weights"]["core"] = {"WW": "100", "PT": "0", "QA": "0"}
        update = admin_client.put("/api/v1/admin/grading-config/", config, format="json")
        self.assertEqual(update.status_code, 200)

        grades = student_client.get("/api/v1/me/grades/?semester=1").data
        self.assertEqual(grades["subjects"][0]["q1"], 86)

        audit = admin_client.get("/api/v1/admin/audit-log/?action=grading_config.update")
        self.assertTrue(any(e["action"] == "grading_config.update" for e in audit.data["results"]))

    def test_student_sees_only_own_grades(self):
        qa = self.create_assessment("QA", 1, 50)
        self.save_scores(qa.data["id"], [{"student_id": self.student.id, "raw": 42}])
        student2_client = self.login_student(self.student2, self.student2_pw)
        grades = student2_client.get("/api/v1/me/grades/?semester=1").data
        self.assertIsNone(grades["subjects"][0]["q1"])

    def test_student_record_privacy(self):
        qa = self.create_assessment("QA", 1, 50)
        self.save_scores(qa.data["id"], [{"student_id": self.student.id, "raw": 42}])

        other_client = APIClient()
        res = login(other_client, "teacher2", "teacherpass123")
        auth(other_client, res.data["access"])
        self.assertEqual(
            other_client.get(f"/api/v1/students/{self.student.id}/record/").status_code, 403
        )

        own_client = APIClient()
        auth(own_client, self.teacher_token)
        res = own_client.get(f"/api/v1/students/{self.student.id}/record/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["student"]["lrn"], self.student.lrn)

        admin_client = APIClient()
        res = login(admin_client, "admin", "adminpass123")
        auth(admin_client, res.data["access"])
        self.assertEqual(
            admin_client.get(f"/api/v1/students/{self.student.id}/record/").status_code, 200
        )

