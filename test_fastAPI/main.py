from fastapi import FastAPI, HTTPException

app = FastAPI()
items =[]

@app.get("/") # root directory
def root():
    return {"Hello": "World"} # this is the root directory ie if that app.get("/") is called this root function is called -> this would be my system or main.py

@app.post("/items") # this is how i can add things to a list via the front end 
def create_item(item: str):
    items.append(item)
    return item

@app.get("/items/{item_id}") # this url defines how i can access things from the backend
def get_item(item_id: int) -> str:
    if item_id< len(items):
        return items[item_id]
    else:
        raise HTTPException(status_code= 404, detail="Item not found")
  