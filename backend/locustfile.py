from locust import HttpUser, task, between
import random
import uuid

class FileManagerUser(HttpUser):
    wait_time = between(1, 3)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_ids = []
        self.token = "test_token"  # Replace with actual auth token
    
    @task(3)
    def upload_file(self):
        test_files = [
            ("sample.pdf", "application/pdf"),
            ("sample.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("sample.txt", "text/plain")
        ]
        
        filename, content_type = random.choice(test_files)
        with open(f"test_data/{filename}", "rb") as f:
            response = self.client.post(
                "/api/v1/files/upload",
                files={"file": (filename, f, content_type)},
                headers={"Authorization": f"Bearer {self.token}"},
                name="/api/v1/files/upload"
            )
            
            if response.status_code == 201:
                self.file_ids.append(response.json()["id"])
    
    @task(2) 
    def get_file_info(self):
        if not self.file_ids:
            return
            
        file_id = random.choice(self.file_ids)
        self.client.get(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {self.token}"},
            name="/api/v1/files/[id]"
        )
    
    @task(1)
    def delete_file(self):
        if not self.file_ids:
            return
            
        file_id = random.choice(self.file_ids)
        response = self.client.delete(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {self.token}"},
            name="/api/v1/files/[id]/delete"
        )
        
        if response.status_code == 204:
            self.file_ids.remove(file_id)
    
    @task(1)
    def reindex_file(self):
        if not self.file_ids:
            return
            
        file_id = random.choice(self.file_ids)
        self.client.post(
            f"/api/v1/files/{file_id}/reindex",
            headers={"Authorization": f"Bearer {self.token}"},
            name="/api/v1/files/[id]/reindex"
        )