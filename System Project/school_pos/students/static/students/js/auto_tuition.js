document.addEventListener("DOMContentLoaded", function () {
    const yearLevelField = document.getElementById("id_year_level");
    const tuitionField = document.getElementById("id_tuition_balance");

    if (yearLevelField && tuitionField) {
        yearLevelField.addEventListener("change", function () {
            const defaults = {
                "Grade 11": 10000.00,
                "Grade 12": 11000.00,
                "College 1st Year": 15000.00,
                "College 2nd Year": 15000.00,
                "College 3rd Year": 16000.00,
                "College 4th Year": 16000.00,
            };

            const selected = yearLevelField.value;
            if (defaults[selected] !== undefined) {
                tuitionField.value = defaults[selected].toFixed(2);
            }
        });
    }
});
