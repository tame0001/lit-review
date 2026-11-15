import { DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { PaperDetailResponse } from '../../core/models/paper.model';
import { ApiClient } from '../../core/services/api-client';

export interface ParsedLine {
  text: string;
  linkLabel?: string;
  linkUrl?: string;
}

export interface ParsedSection {
  heading: string;
  lines: ParsedLine[];
  rawLines: string[];
}

@Component({
  selector: 'app-paper-detail',
  imports: [
    DecimalPipe,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSnackBarModule,
  ],
  templateUrl: './paper-detail.html',
  styleUrl: './paper-detail.scss',
})
export class PaperDetail implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(ApiClient);
  private readonly snackBar = inject(MatSnackBar);

  protected readonly citekey = signal('');
  protected readonly itemKey = signal<string | null>(null);
  protected readonly detail = signal<PaperDetailResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly notFound = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly newTag = signal('');
  protected readonly savingTag = signal(false);
  protected readonly updatingBonus = signal(false);
  protected readonly updatingStatus = signal(false);
  protected readonly syncingPaper = signal(false);
  protected readonly analyzingPaper = signal(false);

  protected readonly meta = computed<Record<string, unknown>>(
    () => this.detail()?.metadata ?? {}
  );

  protected readonly title = computed(() => String(this.meta()['title'] ?? this.citekey()));
  protected readonly authors = computed<string[]>(() => {
    const val = this.meta()['authors'];
    return Array.isArray(val) ? val.map(String) : [];
  });
  protected readonly year = computed(() => this.meta()['year'] as number | null);
  protected readonly doi = computed(() => (this.meta()['doi'] as string | null) ?? null);
  protected readonly status = computed(() => String(this.meta()['status'] ?? 'unread'));
  protected readonly priorityScore = computed(() =>
    Number(this.meta()['priority_score'] ?? 0)
  );
  protected readonly manualBonus = computed(() =>
    Number(this.meta()['manual_bonus'] ?? 0)
  );
  protected readonly llmAnalyzed = computed(() => Boolean(this.meta()['llm_analyzed']));
  protected readonly llmSource = computed(() => String(this.meta()['llm_source'] ?? 'neither'));
  protected readonly llmAnalyzedAt = computed(
    () => (this.meta()['llm_analyzed_at'] as string | null) ?? null
  );
  protected readonly tags = computed<string[]>(() => {
    const val = this.meta()['tags'];
    return Array.isArray(val) ? val.map(String) : [];
  });
  protected readonly scite = computed(() => ({
    supporting: Number(this.meta()['scite_supporting'] ?? 0),
    contrasting: Number(this.meta()['scite_contrasting'] ?? 0),
    mentioning: Number(this.meta()['scite_mentioning'] ?? 0),
    total: Number(this.meta()['scite_total_citations'] ?? 0),
  }));

  protected readonly parsedBody = computed(() => {
    const content = this.detail()?.content ?? '';
    return this.parseObsidianMarkdown(content);
  });

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      const ck = params.get('citekey') ?? '';
      this.citekey.set(ck);
      const qKey = this.route.snapshot.queryParamMap.get('key');
      if (qKey) {
        this.itemKey.set(qKey);
      } else {
        this.resolveItemKey(ck);
      }
      this.loadDetail(ck);
    });
  }

  private resolveItemKey(citekey: string): void {
    this.api.getPapers({ limit: 500 }).subscribe({
      next: (papers) => {
        const match = papers.find((p) => p.citekey === citekey);
        if (match) {
          this.itemKey.set(match.key);
        }
      },
      error: () => {},
    });
  }

  loadDetail(citekey: string = this.citekey()): void {
    this.loading.set(true);
    this.notFound.set(false);
    this.error.set(null);

    this.api.getPaperDetail(citekey).subscribe({
      next: (res) => {
        this.detail.set(res);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        if (err?.status === 404) {
          this.notFound.set(true);
        } else {
          this.error.set(err?.error?.detail || 'Failed to load paper details.');
        }
      },
    });
  }

  adjustBonus(delta: number): void {
    if (this.updatingBonus() || !this.detail()) return;
    const nextBonus = Math.round((this.manualBonus() + delta) * 10) / 10;
    this.updatingBonus.set(true);

    this.api.updateManualBonus(this.citekey(), nextBonus).subscribe({
      next: (res) => {
        this.detail.update((d) =>
          d
            ? {
                ...d,
                metadata: {
                  ...d.metadata,
                  manual_bonus: res.manual_bonus,
                  priority_score: res.priority_score,
                },
              }
            : d
        );
        this.updatingBonus.set(false);
      },
      error: () => {
        this.updatingBonus.set(false);
        this.snackBar.open('Could not update manual bonus', 'Close', { duration: 3000 });
      },
    });
  }

  toggleReadStatus(): void {
    if (this.updatingStatus() || !this.detail()) return;
    const nextStatus: 'read' | 'unread' = this.status() === 'read' ? 'unread' : 'read';
    this.updatingStatus.set(true);

    this.api.updatePaperStatus(this.citekey(), nextStatus).subscribe({
      next: (res) => {
        this.detail.update((d) =>
          d ? { ...d, metadata: { ...d.metadata, status: res.status } } : d
        );
        this.updatingStatus.set(false);
        this.snackBar.open(`Marked as ${res.status}`, 'Close', { duration: 3000 });
      },
      error: () => {
        this.updatingStatus.set(false);
        this.snackBar.open('Could not update paper status', 'Close', { duration: 3000 });
      },
    });
  }

  addTag(): void {
    const key = this.itemKey();
    const raw = this.newTag().trim();
    if (!key || !raw || this.savingTag()) return;

    this.savingTag.set(true);
    this.api.addTags(key, [raw]).subscribe({
      next: () => {
        this.newTag.set('');
        this.savingTag.set(false);
        this.snackBar.open(`Synced tag "${raw}" to Zotero & Obsidian`, 'Close', {
          duration: 3000,
        });
        this.loadDetail();
      },
      error: (err) => {
        this.savingTag.set(false);
        this.snackBar.open(err?.error?.detail || 'Failed to sync tag to Zotero', 'Close', {
          duration: 4000,
        });
      },
    });
  }

  syncSinglePaper(force = true): void {
    const key = this.itemKey();
    if (!key || this.syncingPaper()) return;

    this.syncingPaper.set(true);
    this.api.syncPaper(key, force).subscribe({
      next: (res) => {
        this.syncingPaper.set(false);
        this.snackBar.open(
          `Synced (${res.status}, ${res.highlights} highlight(s))`,
          'Close',
          { duration: 3500 }
        );
        this.loadDetail();
      },
      error: (err) => {
        this.syncingPaper.set(false);
        this.snackBar.open(err?.error?.detail || 'Paper sync failed', 'Close', {
          duration: 4000,
        });
      },
    });
  }

  runLlmAnalysis(force = false): void {
    const key = this.itemKey();
    if (!key || this.analyzingPaper()) return;

    this.analyzingPaper.set(true);
    this.api.analyzePaper(key, force).subscribe({
      next: (res) => {
        this.analyzingPaper.set(false);
        this.snackBar.open(
          res.status === 'skipped_already_analyzed'
            ? 'Already analyzed — click "Force Re-analyze" to rerun'
            : `LLM analysis complete (score: ${res.priority_score})`,
          'Close',
          { duration: 4000 }
        );
        this.loadDetail();
      },
      error: (err) => {
        this.analyzingPaper.set(false);
        this.snackBar.open(err?.error?.detail || 'LLM analysis failed', 'Close', {
          duration: 4500,
        });
      },
    });
  }

  private parseObsidianMarkdown(content: string): {
    abstract: string;
    sections: ParsedSection[];
  } {
    const withoutComments = content.replace(/<!--[\s\S]*?-->/g, '');
    const lines = withoutComments.split(/\r?\n/);
    const abstractLines: string[] = [];
    const sections: ParsedSection[] = [];
    let current: ParsedSection | null = null;
    let inAbstract = false;

    for (const line of lines) {
      if (line.startsWith('> [!ABSTRACT]')) {
        inAbstract = true;
        continue;
      }
      if (inAbstract) {
        if (line.startsWith('>')) {
          abstractLines.push(line.replace(/^>\s?/, ''));
          continue;
        }
        inAbstract = false;
      }

      if (line.startsWith('## ')) {
        current = {
          heading: line.replace(/^##\s+/, '').trim(),
          lines: [],
          rawLines: [],
        };
        sections.push(current);
        continue;
      }

      if (current) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('<!--')) continue;
        current.rawLines.push(trimmed);
        current.lines.push(this.parseMarkdownLine(trimmed));
      }
    }

    return {
      abstract: abstractLines.join('\n').trim(),
      sections,
    };
  }

  private parseMarkdownLine(line: string): ParsedLine {
    const clean = line.replace(/^[-*]\s+/, '').replace(/\*\*/g, '').replace(/^\*/, '').replace(/\*$/, '');
    const linkMatch = clean.match(/^(.*?)\s*\(\[([^\]]+)\]\(([^)]+)\)\)\s*$/);
    if (linkMatch) {
      return {
        text: linkMatch[1].trim(),
        linkLabel: linkMatch[2].trim(),
        linkUrl: linkMatch[3].trim(),
      };
    }
    return { text: clean };
  }
}
