import { DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';
import { CollectionItem, PaperSummary } from '../../core/models/paper.model';
import { ApiClient } from '../../core/services/api-client';

export interface HistogramBin {
  id: string;
  label: string;
  min: number;
  max: number;
  count: number;
  percentHeight: number;
}

@Component({
  selector: 'app-reading-queue',
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
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTableModule,
  ],
  templateUrl: './reading-queue.html',
  styleUrl: './reading-queue.scss',
})
export class ReadingQueue implements OnInit {
  private readonly api = inject(ApiClient);
  private readonly snackBar = inject(MatSnackBar);

  protected readonly displayedColumns = ['score', 'paper', 'status', 'llm', 'citations', 'tags'];

  protected readonly papers = signal<PaperSummary[]>([]);
  protected readonly collections = signal<CollectionItem[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly updatingCitekey = signal<string | null>(null);

  // Filters & Pagination
  protected readonly searchQuery = signal('');
  protected readonly statusFilter = signal<'all' | 'unread' | 'read'>('unread');
  protected readonly collectionFilter = signal('');
  protected readonly tagFilter = signal('');
  protected readonly llmFilter = signal<'all' | 'analyzed' | 'unanalyzed'>('all');
  protected readonly selectedBinId = signal<string | null>(null);
  protected readonly pageIndex = signal(0);
  protected readonly pageSize = signal(25);

  protected readonly unreadPapers = computed(() =>
    this.papers().filter((p) => p.status === 'unread')
  );

  protected readonly unreadCount = computed(() => this.unreadPapers().length);
  protected readonly readCount = computed(
    () => this.papers().filter((p) => p.status === 'read').length
  );
  protected readonly analyzedCount = computed(
    () => this.papers().filter((p) => p.llm_analyzed).length
  );

  protected readonly availableTags = computed(() => {
    const tagSet = new Set<string>();
    for (const p of this.papers()) {
      for (const t of p.tags) {
        tagSet.add(t);
      }
    }
    return Array.from(tagSet).sort((a, b) => a.localeCompare(b));
  });

  protected readonly unreadHistogram = computed<HistogramBin[]>(() => {
    const bins = [
      { id: '0-19', label: '0–19', min: -Infinity, max: 20, count: 0 },
      { id: '20-39', label: '20–39', min: 20, max: 40, count: 0 },
      { id: '40-59', label: '40–59', min: 40, max: 60, count: 0 },
      { id: '60-79', label: '60–79', min: 60, max: 80, count: 0 },
      { id: '80+', label: '80+', min: 80, max: Infinity, count: 0 },
    ];

    for (const p of this.unreadPapers()) {
      const score = p.priority_score ?? 0;
      for (const b of bins) {
        if (score >= b.min && score < b.max) {
          b.count += 1;
          break;
        }
      }
    }

    const maxCount = Math.max(1, ...bins.map((b) => b.count));
    return bins.map((b) => ({
      ...b,
      percentHeight: b.count === 0 ? 0 : Math.max(12, Math.round((b.count / maxCount) * 100)),
    }));
  });

  protected readonly filteredPapers = computed(() => {
    const query = this.searchQuery().trim().toLowerCase();
    const status = this.statusFilter();
    const collection = this.collectionFilter();
    const tag = this.tagFilter();
    const llm = this.llmFilter();
    const binId = this.selectedBinId();
    const activeBin = binId
      ? this.unreadHistogram().find((b) => b.id === binId) ?? null
      : null;

    return this.papers()
      .filter((p) => {
        if (status !== 'all' && p.status !== status) return false;
        if (collection && !p.collections.includes(collection)) return false;
        if (tag && !p.tags.includes(tag)) return false;
        if (llm === 'analyzed' && !p.llm_analyzed) return false;
        if (llm === 'unanalyzed' && p.llm_analyzed) return false;
        if (activeBin) {
          const score = p.priority_score ?? 0;
          if (p.status !== 'unread' || score < activeBin.min || score >= activeBin.max) {
            return false;
          }
        }
        if (query) {
          const haystack = [p.title, p.citekey, ...p.authors].join(' ').toLowerCase();
          if (!haystack.includes(query)) return false;
        }
        return true;
      })
      .sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0));
  });

  protected readonly paginatedPapers = computed(() => {
    const start = this.pageIndex() * this.pageSize();
    return this.filteredPapers().slice(start, start + this.pageSize());
  });

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading.set(true);
    this.error.set(null);

    this.api.getCollections().subscribe({
      next: (cols) => this.collections.set(cols),
      error: () => {},
    });

    this.api.getPapers({ limit: 2000 }).subscribe({
      next: (items) => {
        this.papers.set(items);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(
          err?.error?.detail ||
            'Could not connect to the backend API (http://localhost:8000). Make sure the backend server is running.'
        );
        this.loading.set(false);
      },
    });
  }

  toggleHistogramBin(binId: string): void {
    this.selectedBinId.update((current) => (current === binId ? null : binId));
    this.pageIndex.set(0);
  }

  onPageChange(event: PageEvent): void {
    this.pageIndex.set(event.pageIndex);
    this.pageSize.set(event.pageSize);
  }

  resetPage(): void {
    this.pageIndex.set(0);
  }

  clearFilters(): void {
    this.searchQuery.set('');
    this.statusFilter.set('all');
    this.collectionFilter.set('');
    this.tagFilter.set('');
    this.llmFilter.set('all');
    this.selectedBinId.set(null);
    this.pageIndex.set(0);
  }

  adjustBonus(paper: PaperSummary, delta: number): void {
    if (!paper.has_obsidian_note || this.updatingCitekey() === paper.citekey) {
      return;
    }
    const nextBonus = Math.round((paper.manual_bonus + delta) * 10) / 10;
    this.updatingCitekey.set(paper.citekey);

    this.api.updateManualBonus(paper.citekey, nextBonus).subscribe({
      next: (res) => {
        this.papers.update((list) =>
          list.map((item) =>
            item.citekey === paper.citekey
              ? { ...item, manual_bonus: res.manual_bonus, priority_score: res.priority_score }
              : item
          )
        );
        this.updatingCitekey.set(null);
      },
      error: () => {
        this.updatingCitekey.set(null);
        this.snackBar.open('Could not update manual bonus', 'Close', { duration: 3000 });
      },
    });
  }
}
