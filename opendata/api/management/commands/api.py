import os
import yaml
import json
import sys
from multiprocessing import Process
from django.core.management.base import BaseCommand
from api import models

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))

OPENDATA_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))

DATA_DIR = os.path.join(os.path.dirname(OPENDATA_DIR), "data")

EMERGENCY_DATASET_PATH = os.path.join(DATA_DIR, "emergency.yml")

FACULTIES_DATASET_PATH = os.path.join(DATA_DIR, "faculties.yml")

PROVINCES_DATASET_PATH = os.path.join(DATA_DIR, "provinces.yml")

UNIVERSITIES_DATASET_PATH = os.path.join(DATA_DIR, "universities.yml")

COURSES_DATASET_PATH = [
    os.path.join(DATA_DIR, 'formations', x) for x in os.listdir(os.path.join(DATA_DIR, 'formations'))
]

class Data(object):      

    @staticmethod
    def get_emergency():
        with open(EMERGENCY_DATASET_PATH) as fp:
            data = yaml.safe_load(fp)
            
        return data

    @staticmethod
    def get_faculties():
        with open(FACULTIES_DATASET_PATH) as fp:
            data = yaml.safe_load(fp)
            
        return data

    @staticmethod
    def get_provinces():
        with open(PROVINCES_DATASET_PATH) as fp:
            data = yaml.safe_load(fp)
            
        return data

    @staticmethod
    def get_universities():
        with open(UNIVERSITIES_DATASET_PATH) as fp:
            data = yaml.safe_load(fp)
            
        return data

    @staticmethod
    def get_courses():
        courses = []
        for file in COURSES_DATASET_PATH:
            with open(file, 'r+') as fp:
                current_file_content = yaml.safe_load(fp)
            current_courses = current_file_content["courses"]
            for course in current_courses:
                course["university"] = current_file_content["id"]
            courses += current_courses


        return courses

class Command(BaseCommand):
    
    help = 'Add records to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data',
            required=False,
            choices=["load", "display", "delete"],
            dest='action',
            help='Specify action',
        )

    def handle(self, *args, **options):
        action = options['action']

        if str(action) == "load":
            self.load()
        
        if str(action) == "display":
            self.display()

        if str(action) == "delete":
            self.delete()

    def load(self):
        self.stdout.write('Loading data to database...')
        self.load_provinces()
        self.load_universities()
        self.load_faculties()
        self.load_courses()
        self.stdout.write('Loading data to database...done.')
    
    def load_universities(self):
        self.stdout.write('Loading universities data to database...')
        universities = Data.get_universities()

        for university in universities:
            current_university = models.University(
                short_name = university["id"],
                long_name = university["name"],
                address = university["address"],
                phone = university["phone"],
                email = university["email"],
                url = university["url"],
                status = university["type"]
            )
            current_university.save()

            for city in university["cities"]:
                try:
                    current_university.cities.add(models.City.objects.get(name=str(city).upper()))
                except models.City.DoesNotExist:
                    print ("City : %s isn't in the database yet." %(city))
                else:
                    print ("City : %s is in the database." %(city))

        self.stdout.write('Loading universities data to database...done.')

    def load_courses(self):
        self.stdout.write("Loading courses data to database...")
        courses = Data.get_courses()
        for course in courses:
            try:
                current_course = models.Course(
                    name = course["name"],
                    description = course["description"],
                    prerequisite = course["prerequisite"],
                    years_of_study = course["yearsofstudy"],
                    faculty = course["faculty"],
                    university = models.University.objects.get(short_name=course["university"])
                )
                current_course.save()

                for field in course["fields"]:
                        current_field = models.Field(name=field)
                        current_field.save()
                        current_course.fields.add(current_field)   

                for profession in course["roles"]:
                    current_profession = models.Profession(name=profession)
                    current_profession.save()
                    current_course.professions.add(current_profession)
            except models.University.DoesNotExist:
                print("University isn't in the database yet.")
        self.stdout.write("Loading courses data to database...done.")

    def load_faculties(self):
        self.stdout.write('Loading faculties data to database...')
        faculties = Data.get_faculties()
        for university in faculties:
            try:
                current_faculties = university["faculties"]
                for faculty in current_faculties:
                    current_faculty = models.Faculty(
                        short_name = faculty["id"],
                        long_name = faculty["name"],
                        city = models.City.objects.get(name=str(faculty["city"]).upper()),
                        university = models.University.objects.get(short_name=university["id"])   
                    )
                    current_faculty.save()
                    for field in faculty["fields"]:
                        current_field = models.Field(name=field)
                        current_field.save()
                        current_faculty.fields.add(current_field)
            except models.City.DoesNotExist:
                    print("City isn't in the database yet.")
            except models.University.DoesNotExist:
                    print("University isn't in the database yet.")  

        self.stdout.write('Loading faculties data to database...done.')

    def load_provinces(self):
        self.stdout.write('Loading province data to database...')
        provinces = Data.get_provinces()
        for province in provinces:
            p = Process(target=self.load_province, args=(province,))
            p.start()
            p.join()
        self.stdout.write('Loading province data to database...done.')

    def load_province(self, province):
        current_province = models.Province(name=province["lib_dep"])
        current_province.save()
        for commune in province["communes"]:
            city = models.City(name=commune["lib_com"])
            city.save()
            for arrondissement in commune["arrondissements"]:
                district = models.District(name=arrondissement['lib_arrond'])
                district.save()
                for quartier in arrondissement["quartiers"]:
                    neighborhood = models.Neighborhood(name=quartier['lib_quart'])
                    neighborhood.save()
                    district.neighborhoods.add(neighborhood)
                city.districts.add(district)
            current_province.cities.add(city)            
    
        
    def display(self):
        self.stdout.write("Total provinces %s" %(len(models.Province.objects.all())))
        self.stdout.write("Total universities %s" %(len(models.University.objects.all())))
        self.stdout.write("Total Faculties %s" %(len(models.Faculty.objects.all())))
        self.stdout.write("Total Courses %s" %(len(models.Course.objects.all())))

    def delete(self):
        self.stdout.write("Deleting %s provinces..." %(len(models.Province.objects.all())))
        models.Province.objects.all().delete()
        self.stdout.write("Total provinces after delete %s" %(len(models.Province.objects.all())))
        
        self.stdout.write("Deleting %s universities..." %(len(models.University.objects.all())))
        models.University.objects.all().delete()
        self.stdout.write("Total universities after delete %s" %(len(models.University.objects.all())))
        
        self.stdout.write("Deleting %s Faculties..." %(len(models.Faculty.objects.all())))
        models.Faculty.objects.all().delete()
        self.stdout.write("Total Faculties after delete %s" %(len(models.Faculty.objects.all())))

        self.stdout.write("Deleting %s Courses..." %(len(models.Course.objects.all())))
        models.Course.objects.all().delete()
        self.stdout.write("Total Courses %s" %(len(models.Course.objects.all())))
        
