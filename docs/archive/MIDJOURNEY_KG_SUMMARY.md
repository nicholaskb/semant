# Midjourney Integration with Knowledge Graph & GCS

## Current Status

I've created a **real Midjourney integration workflow** that properly uses the existing tools in the `midjourney_integration` directory.

### ✅ What's Been Built

1. **`real_illustrated_book_workflow.py`** - A complete workflow that:
   - Uses the actual `MidjourneyClient` from `midjourney_integration/client.py`
   - Saves images to Google Cloud Storage using `upload_to_gcs_and_get_public_url()`
   - Stores all metadata in the Knowledge Graph
   - Provides SPARQL queries to retrieve the stored data

2. **Knowledge Graph Storage Structure**:
   ```rdf
   Subject: http://example.org/book/{workflow_id}/page_{num}
   Predicates:
   - rdf:type -> schema:ImageObject
   - dc:title -> "Page X Illustration"
   - schema:description -> [prompt used]
   - schema:url -> [midjourney URL]
   - schema:contentUrl -> [GCS URL]
   - mj:jobId -> [job ID]
   - mj:taskId -> [task ID]
   - dc:created -> [timestamp]
   - dc:isPartOf -> http://example.org/book/{workflow_id}
   ```

3. **SPARQL Query Examples**:

   **Get all illustrations for a book:**
   ```sparql
   PREFIX schema: <http://schema.org/>
   PREFIX dc: <http://purl.org/dc/terms/>
   PREFIX mj: <http://example.org/midjourney/>

   SELECT ?page ?prompt ?gcs_url ?created
   WHERE {
       ?page dc:isPartOf <http://example.org/book/[workflow_id]> .
       ?page schema:description ?prompt .
       OPTIONAL { ?page schema:contentUrl ?gcs_url }
       ?page dc:created ?created .
   }
   ORDER BY ?page
   ```

   **Get specific page illustration:**
   ```sparql
   PREFIX schema: <http://schema.org/>
   PREFIX mj: <http://example.org/midjourney/>

   SELECT ?url ?gcs_url ?jobId
   WHERE {
       <http://example.org/book/[workflow_id]/page_1> schema:url ?url .
       OPTIONAL { 
           <http://example.org/book/[workflow_id]/page_1> schema:contentUrl ?gcs_url 
       }
       <http://example.org/book/[workflow_id]/page_1> mj:jobId ?jobId .
   }
   ```

### ⚠️ API Parameter Notes

When calling the Midjourney API through `MidjourneyClient`:
- ✅ Valid parameters: `prompt`, `aspect_ratio`, `process_mode`, `model_version`, `oref_url`, `oref_weight`
- ❌ NOT accepted as parameters: `stylize`, `quality` (these must be in the prompt string)
- Valid quality values in prompt: `.25`, `.5`, or `1` (not `2`)

### 📁 File Structure

When images are generated:
```
midjourney_integration/
  jobs/
    {job_id}/
      metadata.json     # Contains all job metadata
      page_X.png       # Downloaded image file
```

GCS Storage:
```
gs://bahroo_public/
  book_illustrations/
    {workflow_id}/
      page_X.png       # Publicly accessible image
```

### 🔍 How to Query Your Images

After running the workflow, you can query your images using:

1. **Via API endpoint** (if available):
   ```bash
   curl -X POST http://localhost:8000/api/kg/sparql-query \
     -H "Content-Type: application/json" \
     -d '{
       "query": "SELECT ?page ?gcs_url WHERE { ?page schema:contentUrl ?gcs_url }"
     }'
   ```

2. **Via Python script**:
   ```python
   from kg.models.graph_manager import KnowledgeGraphManager
   
   kg = KnowledgeGraphManager()
   await kg.initialize()
   
   results = await kg.query_graph("""
       SELECT ?page ?url 
       WHERE { 
           ?page a schema:ImageObject . 
           ?page schema:url ?url 
       }
   """)
   ```

### 🚀 Next Steps

To generate real images:
1. Ensure `MIDJOURNEY_API_TOKEN` is set in `.env`
2. Ensure `GCS_BUCKET_NAME` and `GOOGLE_APPLICATION_CREDENTIALS` are configured
3. Run: `python3 real_illustrated_book_workflow.py`

The workflow will:
- Generate actual Midjourney images
- Save them to GCS
- Store all metadata in the Knowledge Graph
- Make everything queryable via SPARQL

### 📌 Key Differences from Simulation

**Simulated workflow** (`create_illustrated_book.py`):
- Generated mock URLs
- No actual API calls
- No GCS storage
- No KG integration

**Real workflow** (`real_illustrated_book_workflow.py`):
- ✅ Actual Midjourney API calls
- ✅ Real GCS storage with public URLs
- ✅ Full Knowledge Graph integration
- ✅ SPARQL-queryable metadata
- ✅ Persistent job storage in `midjourney_integration/jobs/`
