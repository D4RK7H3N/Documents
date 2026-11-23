from django import forms
from .models import Student  

class StudentEnrollmentForm(forms.ModelForm):
    # Add track_strand as ChoiceField for proper dropdown
    track_strand = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_track_strand"
        }),
        label="Track/Strand"
    )
    
    # Add section as ChoiceField for proper dropdown
    section = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_section"
        })
    )
    
    class Meta:
        model = Student
        fields = [
            "lrn", "first_name", "middle_name", "last_name",
            "date_of_birth", "gender", "nationality", "address",
            "contact_number", "email",

            "guardian_name", "guardian_relationship",
            "guardian_occupation", "guardian_address",

            "previous_school", "last_grade_completed", "is_als_graduate",
            
            "level_type", "shs_grade", "college_year",
            "track_strand", "section", "course",
            
            "current_grade_level", "section_strand_course", "academic_records",

            "blood_type", "medical_conditions", "immunization_records",
            "preferred_hospital", "health_insurance",

            "date_of_enrollment", "enrollment_status",
            "payment_details", "scholarship_discount",
            "photo", "extracurricular", "tuition_balance"
        ]

        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "date_of_enrollment": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "enrollment_status": forms.Select(attrs={"class": "form-select"}),
            
            "level_type": forms.Select(attrs={"class": "form-select"}),
            "shs_grade": forms.Select(attrs={"class": "form-select"}),
            "college_year": forms.Select(attrs={"class": "form-select"}),
            
            # REMOVED track_strand from widgets - defined as ChoiceField above
            # REMOVED section from widgets - defined as ChoiceField above
            
            "course": forms.TextInput(attrs={
                "class": "form-control", 
                "placeholder": "For college: BSIT, BSBA, etc."
            }),
            "is_als_graduate": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            
            "current_grade_level": forms.Select(attrs={"class": "form-select"}),
            "address": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "guardian_address": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "academic_records": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "medical_conditions": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "immunization_records": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "payment_details": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "scholarship_discount": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "extracurricular": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            
            "lrn": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "middle_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "nationality": forms.TextInput(attrs={"class": "form-control"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "guardian_name": forms.TextInput(attrs={"class": "form-control"}),
            "guardian_relationship": forms.TextInput(attrs={"class": "form-control"}),
            "guardian_occupation": forms.TextInput(attrs={"class": "form-control"}),
            "guardian_address": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "previous_school": forms.TextInput(attrs={"class": "form-control"}),
            "last_grade_completed": forms.TextInput(attrs={"class": "form-control"}),
            "section_strand_course": forms.TextInput(attrs={"class": "form-control"}),
            "blood_type": forms.TextInput(attrs={"class": "form-control"}),
            "preferred_hospital": forms.TextInput(attrs={"class": "form-control"}),
            "health_insurance": forms.TextInput(attrs={"class": "form-control"}),
            "tuition_balance": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate track/strand choices
        track_strand_choices = [
            ('', '--- Select Track/Strand ---'),
            ('STEM', 'Science, Technology, Engineering, and Mathematics (STEM)'),
            ('ABM', 'Accountancy, Business and Management (ABM)'),
            ('HUMSS', 'Humanities and Social Sciences (HUMSS)'),
            ('GAS', 'General Academic Strand (GAS)'),
            ('ICT', '(ICT) Computer Servicing System NC I'),
            ('ICT .NET', '(ICT) .NET Programming NC II'),
            ('ICT JAVA', '(ICT) JAVA Programming NC III'),
            ('Industrial', 'Industrial Arts'),
            ('Home Economics', 'Home Economics'),
            ('AFA', 'Agri-Culture NCI'),
        ]
        
        self.fields['track_strand'].choices = track_strand_choices
        
        # Populate section choices from database
        existing_sections = Student.objects.exclude(
            section__isnull=True
        ).exclude(
            section=''
        ).values_list('section', flat=True).distinct().order_by('section')
        
        # Define predefined sections
        predefined_sections = [
            'Section A', 'Section B', 'Section C', 'Section D', 'Section E',
            'Diamond', 'Gold', 'Silver', 'Pearl', 'Ruby', 'Emerald', 'Sapphire'
        ]
        
        # Combine and remove duplicates
        all_sections = sorted(set(list(existing_sections) + predefined_sections))
        
        # Create choices with empty option first
        section_choices = [('', '--- Select Section ---')]
        section_choices.extend([(section, section) for section in all_sections])
        
        self.fields['section'].choices = section_choices