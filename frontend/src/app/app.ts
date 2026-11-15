import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { HealthStatus } from './core/models/paper.model';
import { ApiClient } from './core/services/api-client';

@Component({
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule,
  ],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App implements OnInit {
  private readonly api = inject(ApiClient);
  private readonly snackBar = inject(MatSnackBar);

  protected readonly health = signal<HealthStatus | null>(null);
  protected readonly syncing = signal(false);

  ngOnInit(): void {
    this.api.getHealth().subscribe({
      next: (status) => this.health.set(status),
      error: () => this.health.set(null),
    });
  }

  triggerSync(): void {
    if (this.syncing()) return;
    this.syncing.set(true);

    this.api.syncAll(false).subscribe({
      next: (res) => {
        this.syncing.set(false);
        this.snackBar.open(`Synced ${res.affected_papers} paper(s) from Zotero`, 'Close', {
          duration: 3500,
        });
      },
      error: () => {
        this.syncing.set(false);
        this.snackBar.open('Sync failed — check backend & Zotero connection', 'Close', {
          duration: 4500,
        });
      },
    });
  }
}
