from locust import HttpUser, task, between, SequentialTaskSet

class UserBehavior(SequentialTaskSet):
    """
    Defines the sequence of tasks that a user will perform.
    """

    def on_start(self):
        """
        Simulate user login.
        """
        self.client.post("/token/", json={"username": "admin", "password": "password"})

    @task
    def index(self):
        """
        Simulate accessing the index page.
        """
        self.client.get("/")

    @task
    def secure_data(self):
        """
        Simulate accessing secure data.
        """
        self.client.get("/secure-data/")

    @task
    def create_animal(self):
        """
        Simulate creating a new animal.
        """
        self.client.post("/animals/", json={"name": "Leo", "species": "Lion", "age": 4})

    @task
    def update_animal(self):
        """
        Simulate updating an existing animal.
        """
        self.client.put("/animals/1", json={"name": "Leo", "species": "Lion", "age": 5})

    @task
    def delete_animal(self):
        """
        Simulate deleting an animal.
        """
        self.client.delete("/animals/1")

    @task
    def upsert_animal(self):
        """
        Simulate upserting an animal.
        """
        self.client.post("/upsert/", data={"name": "Leo", "species": "Lion", "age": 5})

class WebsiteUser(HttpUser):
    """
    Represents a user that performs the tasks defined in UserBehavior.
    """
    tasks = [UserBehavior]
    wait_time = between(1, 5)