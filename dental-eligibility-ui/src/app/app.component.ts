import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-root',
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  currentPage: string = 'dashboard';
  
  navigationItems = [
    { label: '📊 Dashboard', value: 'dashboard' },
    { label: '📤 Data Upload', value: 'data-upload' },
    { label: '⚡ Batch Processing', value: 'batch-processing' },
    { label: '🔍 Member Search', value: 'member-search' },
    { label: '📈 Analytics', value: 'analytics' }
  ];

  setCurrentPage(page: string): void {
    this.currentPage = page;
  }

  getCurrentPageLabel(): string {
    const item = this.navigationItems.find(item => item.value === this.currentPage);
    return item ? item.label : '📊 Dashboard';
  }
}
