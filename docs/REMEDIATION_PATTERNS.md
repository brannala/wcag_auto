# Accessibility Remediation Patterns

This document provides common patterns for fixing accessibility issues in Canvas course content.

## Image Alt Text Patterns

### Pattern 1: Informational Images

**Before:**
```html
<img src="cell-diagram.png">
```

**After:**
```html
<img src="cell-diagram.png" alt="Diagram showing the major components of an animal cell including nucleus, mitochondria, and cell membrane">
```

**Decision criteria:**
- Does the image convey information not available in surrounding text?
- What would a screen reader user need to know?
- Describe content and purpose, not appearance

### Pattern 2: Decorative Images

**Before:**
```html
<img src="decorative-line.png">
```

**After:**
```html
<img src="decorative-line.png" alt="">
```

**When to use empty alt:**
- Purely decorative borders, backgrounds, spacers
- Icons next to text that already conveys the same information
- Decorative flourishes with no informational value

### Pattern 3: Images of Text

**Before:**
```html
<img src="welcome-banner.png">
```

**After:**
```html
<img src="welcome-banner.png" alt="Welcome to Biology 101: Introduction to Cell Biology">
```

**Better alternative:**
```html
<h1 class="banner-style">Welcome to Biology 101: Introduction to Cell Biology</h1>
```

### Pattern 4: Complex Images (Charts, Graphs)

**Before:**
```html
<img src="enrollment-chart.png">
```

**After:**
```html
<figure>
  <img src="enrollment-chart.png" alt="Bar chart showing student enrollment trends">
  <figcaption>
    <details>
      <summary>Chart data description</summary>
      <p>Enrollment by year: 2020: 450 students, 2021: 520 students, 
      2022: 610 students, 2023: 680 students. Overall increase of 51%.</p>
    </details>
  </figcaption>
</figure>
```

### Pattern 5: Linked Images

**Before:**
```html
<a href="syllabus.pdf"><img src="pdf-icon.png"></a>
```

**After:**
```html
<a href="syllabus.pdf"><img src="pdf-icon.png" alt="Download Course Syllabus (PDF, 150KB)"></a>
```

Or better:
```html
<a href="syllabus.pdf">
  <img src="pdf-icon.png" alt="" aria-hidden="true">
  Download Course Syllabus (PDF, 150KB)
</a>
```

## Link Text Patterns

### Pattern 1: Generic Link Text

**Before:**
```html
<p>For the assignment guidelines, <a href="guidelines.html">click here</a>.</p>
```

**After:**
```html
<p>Read the <a href="guidelines.html">assignment guidelines</a> before starting.</p>
```

### Pattern 2: URL as Link Text

**Before:**
```html
<a href="https://www.cdc.gov/coronavirus/">https://www.cdc.gov/coronavirus/</a>
```

**After:**
```html
<a href="https://www.cdc.gov/coronavirus/">CDC COVID-19 Information</a>
```

### Pattern 3: "Read More" Links

**Before:**
```html
<article>
  <h3>Introduction to Genetics</h3>
  <p>Genetics is the study of genes...</p>
  <a href="genetics.html">Read more</a>
</article>
```

**After (Option A - descriptive text):**
```html
<article>
  <h3>Introduction to Genetics</h3>
  <p>Genetics is the study of genes...</p>
  <a href="genetics.html">Read more about Introduction to Genetics</a>
</article>
```

**After (Option B - aria-label):**
```html
<article>
  <h3>Introduction to Genetics</h3>
  <p>Genetics is the study of genes...</p>
  <a href="genetics.html" aria-label="Read more about Introduction to Genetics">Read more</a>
</article>
```

### Pattern 4: Document Links

**Before:**
```html
<a href="readings/chapter5.pdf">Chapter 5</a>
```

**After:**
```html
<a href="readings/chapter5.pdf">Chapter 5: Cellular Respiration (PDF, 2.3MB)</a>
```

### Pattern 5: External Links

**Before:**
```html
<a href="https://pubmed.ncbi.nlm.nih.gov/">PubMed</a>
```

**After:**
```html
<a href="https://pubmed.ncbi.nlm.nih.gov/" target="_blank" rel="noopener">
  PubMed (opens in new tab)
  <span class="visually-hidden">, external link</span>
</a>
```

## Heading Structure Patterns

### Pattern 1: Missing Document Hierarchy

**Before:**
```html
<p><strong>Course Overview</strong></p>
<p>This course covers...</p>
<p><strong>Learning Objectives</strong></p>
```

**After:**
```html
<h1>Course Overview</h1>
<p>This course covers...</p>
<h2>Learning Objectives</h2>
```

### Pattern 2: Skipped Heading Levels

**Before:**
```html
<h1>Module 3: Research Methods</h1>
<h4>Quantitative Methods</h4>
```

**After:**
```html
<h1>Module 3: Research Methods</h1>
<h2>Quantitative Methods</h2>
```

### Pattern 3: Multiple H1 Tags

**Before:**
```html
<h1>Course Title</h1>
<h1>Week 1</h1>
<h1>Week 2</h1>
```

**After:**
```html
<h1>Course Title</h1>
<h2>Week 1</h2>
<h2>Week 2</h2>
```

## Table Accessibility Patterns

### Pattern 1: Simple Data Table

**Before:**
```html
<table>
  <tr>
    <td>Assignment</td>
    <td>Due Date</td>
    <td>Points</td>
  </tr>
  <tr>
    <td>Essay 1</td>
    <td>Sept 15</td>
    <td>100</td>
  </tr>
</table>
```

**After:**
```html
<table>
  <caption>Assignment Schedule for Fall 2024</caption>
  <thead>
    <tr>
      <th scope="col">Assignment</th>
      <th scope="col">Due Date</th>
      <th scope="col">Points</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Essay 1</td>
      <td>Sept 15</td>
      <td>100</td>
    </tr>
  </tbody>
</table>
```

### Pattern 2: Table with Row Headers

**Before:**
```html
<table>
  <tr>
    <td></td>
    <td>Week 1</td>
    <td>Week 2</td>
  </tr>
  <tr>
    <td>Reading</td>
    <td>Ch 1-2</td>
    <td>Ch 3-4</td>
  </tr>
</table>
```

**After:**
```html
<table>
  <caption>Weekly Reading Schedule</caption>
  <thead>
    <tr>
      <td></td>
      <th scope="col">Week 1</th>
      <th scope="col">Week 2</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">Reading</th>
      <td>Ch 1-2</td>
      <td>Ch 3-4</td>
    </tr>
  </tbody>
</table>
```

### Pattern 3: Layout Tables (convert to CSS)

**Before:**
```html
<table>
  <tr>
    <td><img src="instructor.jpg"></td>
    <td>
      <p>Dr. Smith</p>
      <p>Office: Room 301</p>
    </td>
  </tr>
</table>
```

**After:**
```html
<div class="instructor-card">
  <img src="instructor.jpg" alt="Dr. Smith">
  <div class="instructor-info">
    <p><strong>Dr. Smith</strong></p>
    <p>Office: Room 301</p>
  </div>
</div>
```

Or if table must remain:
```html
<table role="presentation">
  <!-- table content unchanged -->
</table>
```

## Form Accessibility Patterns

### Pattern 1: Unlabeled Input

**Before:**
```html
<input type="text" name="email">
```

**After:**
```html
<label for="email-input">Email Address</label>
<input type="email" id="email-input" name="email">
```

### Pattern 2: Required Fields

**Before:**
```html
<label>Name *</label>
<input type="text">
```

**After:**
```html
<label for="name-input">
  Name <span class="required" aria-hidden="true">*</span>
  <span class="visually-hidden">(required)</span>
</label>
<input type="text" id="name-input" required aria-required="true">
```

### Pattern 3: Error Messages

**Before:**
```html
<input type="email" class="error">
<span class="error-text">Invalid email</span>
```

**After:**
```html
<label for="email">Email Address</label>
<input type="email" id="email" aria-describedby="email-error" aria-invalid="true">
<span id="email-error" class="error-text" role="alert">
  Please enter a valid email address (e.g., name@example.com)
</span>
```

## Color and Contrast Patterns

### Pattern 1: Insufficient Text Contrast

**Before:**
```html
<p style="color: #999;">Important note about the assignment.</p>
```

**After:**
```html
<p style="color: #595959;">Important note about the assignment.</p>
```

Or use CSS class:
```html
<p class="note">Important note about the assignment.</p>
```
```css
.note { color: #595959; } /* Meets 4.5:1 on white */
```

### Pattern 2: Color-Only Information

**Before:**
```html
<p>Required fields are marked in <span style="color:red">red</span>.</p>
<label style="color:red">Email</label>
```

**After:**
```html
<p>Required fields are marked with an asterisk (*).</p>
<label>Email <span aria-hidden="true">*</span><span class="visually-hidden">(required)</span></label>
```

## Language Patterns

### Pattern 1: Missing Page Language

**Before:**
```html
<html>
<head>...
```

**After:**
```html
<html lang="en">
<head>...
```

### Pattern 2: Foreign Language Content

**Before:**
```html
<p>As the French say, c'est la vie.</p>
```

**After:**
```html
<p>As the French say, <span lang="fr">c'est la vie</span>.</p>
```

## Visually Hidden Text Pattern

For cases where you need text for screen readers but not visual display:

```css
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

Usage:
```html
<a href="twitter.com/university">
  <img src="twitter-icon.png" alt="">
  <span class="visually-hidden">University Twitter (opens in new tab)</span>
</a>
```
