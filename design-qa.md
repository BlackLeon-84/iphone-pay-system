# Design QA

## Evidence

- Source visual truth: `/home/edith/.codex/generated_images/019f40a4-9cff-77c0-9ab5-58f6495bbe5d/exec-4daa916b-96a0-41a4-a548-59882e3d2d10.png`
- Browser-rendered desktop: `/DATA/Documents/project/iphone-pay-system/design-preview-2026-09-13/daily-desktop.png`
- Browser-rendered mobile: `/DATA/Documents/project/iphone-pay-system/design-preview-2026-09-13/daily-mobile375.png`
- Browser-rendered tablet: `/DATA/Documents/project/iphone-pay-system/design-preview-2026-09-13/daily-tablet740.png`
- Browser-rendered report: `/DATA/Documents/project/iphone-pay-system/design-preview-2026-09-13/report-mobile375.png`
- Combined comparison: `/DATA/Documents/project/iphone-pay-system/design-preview-2026-09-13/qa-side-by-side.png`
- Source pixels: 1627 x 973
- Desktop implementation: 1440 x 1100 CSS px, device scale factor 1
- Mobile implementation: 375 x 812 and 390 x 844 CSS px, device scale factor 1
- Tablet implementation: 740 x 920 CSS px, device scale factor 1
- State: `테스트` 계정, daily input and monthly report, white theme

## Findings

No actionable P0, P1, or P2 differences remain.

- Typography: Pretendard-first system stack, strong black headings, tabular monetary figures, and neutral supporting text match the selected direction. The implementation uses slightly smaller desktop type to make room for the required calendar.
- Spacing and layout: desktop keeps navigation, working area, and live total as distinct regions. Mobile becomes one column while calendar rows and action controls retain their intended horizontal grouping.
- Colors: white, near-black, cool gray, restrained cobalt, green saved state, and red deductions are consistent. Native selected controls were explicitly aligned to cobalt.
- Image quality: the source and implementation contain no required photographic or illustrated assets.
- Copy: labels use the current payroll vocabulary. Test-only state is identified without placing operational warnings inside the report capture.

The large calendar is an intentional addition after the source mockup because missed-entry checking was added as a requirement. It moves the desktop input area lower than the original mockup, but retains the source's working-area and live-total relationship.

## Focused Evidence

Mobile captures at 375px and 390px were checked separately because the seven-column calendar,
long currency values, fixed bottom navigation, and report capture cannot be judged reliably in the desktop comparison.
The 375px capture has no horizontal overflow, the month title remains on one line, and report amounts do not clip.

## Comparison History

1. Initial capture: login state was captured before the Streamlit rerun completed. Capture wait condition was changed to the destination screen title.
2. First mobile pass: Streamlit collapsed calendar columns vertically and left desktop identity controls above the page. Mobile column rules were narrowed, calendar rows restored to seven columns, and desktop identity controls hidden.
3. Second mobile pass: the month title wrapped and selected navigation styling was inconsistent. Header proportions and selected-control colors were corrected.
4. Final capture: desktop, 390px, and 375px had zero horizontal overflow and zero console/page errors.
5. Browser-comment follow-up: 740px retained the desktop two-column layout because the responsive breakpoint ended at 700px. The breakpoint was raised to 900px; the 740px recheck now uses one column with zero overflow and zero console/page errors.

## Primary Interactions Tested

- Login, all three navigation destinations, month selection, and report mode
- All six employee variants and overtime visibility
- Off-day save followed by normal data entry and save
- Responsive calendar and fixed mobile navigation

## Follow-up Polish

- P3: native Streamlit number steppers remain visually more utilitarian than the source mockup's compact custom steppers.

final result: passed
