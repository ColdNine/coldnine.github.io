# TODO
- Making daily auto scheduler which performs crawling then posting by github actions pipline and pages (blog)
- Extract core keywords and summary from IT(AI/SW) part articles in Korean ETNews

## Workflow
1. GitHub Actions (daily scheduling)
2. Python Crawling Script (retrieve keywords which stands for each article for IT News in https://m.etnews.com
3. Core Keywords & Summary of an IT article using LLM API or TextRank(TF-IDF) or Semantic Methodologies (make it to be selectable in config)
4. Create Markdown file and commit/push to GitHub Repo (auto build/deploy in GitHub Pages)

## References
- Keyword Extraction: e.g., KeyBERT, KoNLPy
- Summarize: e.g., TextRank
- Jekyll
- ETNews URL Format: https://etnews.com/YYYYMMDD000000 (6 digits following as an id)
- ETNews AI/SW Section: https://m.etnews.com/news/section.html?id1=04
