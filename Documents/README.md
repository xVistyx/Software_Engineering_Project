# Software_Engineering_Project

## AI Focus Browser Extension

An AI-powered Google Chrome extension designed to help users stay focused by automatically deciding whether the websites they visit are relevant to their current task.

Instead of manually creating a list of blocked websites, the user simply tells the extension what they want to focus on.

For example:

> "Today I am studying mathematics."

The extension then analyzes websites as the user opens them and determines whether they are relevant to studying mathematics.

If the website is relevant, access is allowed.  
If the website is considered distracting or unrelated, the extension blocks the page.

---

## How It Works

1. The user opens the Chrome extension.
2. The user enters their current goal or task.

Example:

`Study mathematics for my calculus exam`

3. Whenever the user visits a website, the extension collects basic information about the page, such as:
   - Page title
   - URL/domain
   - Meta description
   - Other relevant page metadata

4. The website information and the user's current goal are sent to an AI model.

5. The AI classifies the website as:

   - ✅ **Relevant** – website is allowed.
   - ❌ **Distracting** – website is blocked.

### Example

Current goal:

`Study mathematics`

| Website | AI Decision |
|---|---|
| wolframalpha.com | ✅ Allow |
| khanacademy.org | ✅ Allow |
| wikipedia.org/wiki/Calculus | ✅ Allow |
| instagram.com | ❌ Block |
| tiktok.com | ❌ Block |
| youtube.com/watch?v=calculus_tutorial | ✅ Allow |
| youtube.com/watch?v=random_memes | ❌ Block |

The important difference compared to traditional website blockers is that the system evaluates the **content and context of the page**, rather than blocking an entire domain.

For example, YouTube could be allowed when watching a mathematics tutorial but blocked when opening unrelated entertainment.

---

## Main Features

- AI-based website classification
- User-defined focus goal
- Automatic website blocking
- Context-aware decisions
- Website metadata analysis
- Ability to allow useful content on normally distracting platforms
- Simple Chrome extension interface
- Focus session controls

---

## System Flow

```text
User defines goal
        ↓
User opens website
        ↓
Extension reads website metadata
        ↓
Metadata + Goal sent to AI
        ↓
AI determines relevance
        ↓
   ┌───────────────┐
   │               │
Relevant       Not Relevant
   │               │
Allow Page      Block Page


How to run:
## Conda Environment Setup

This project uses **Conda** so everyone uses the same Python version and dependencies.

### 1. Install Miniconda

**macOS**

```bash
brew install miniconda
conda init zsh
```

Restart the terminal.

**Windows**

Install Miniconda from:

https://docs.conda.io/projects/miniconda/en/latest/

Then open Anaconda Prompt or restart PowerShell.

---

### 2. Create the Environment

From the project folder:

```bash
conda env create -f environment.yml
```

This creates the environment:

```text
LockDownProject
```

### 3. Activate It

```bash
conda activate LockDownProject
```

Check that it works:

```bash
python --version
```

The project uses Python 3.12.

### 4. Update the Environment

If `environment.yml` changes after pulling from Git:

```bash
conda env update -f environment.yml --prune
```

### 5. Deactivate

```bash
conda deactivate
```

### VS Code

Open:

```text
Python: Select Interpreter
```

and select the Python interpreter from:

```text
LockDownProject
```
